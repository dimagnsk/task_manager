import sqlite3
import time
from PyQt5.QtCore    import QAbstractItemModel, Qt, QModelIndex, QVariant, pyqtSignal, QMutex
from PyQt5.QtGui     import QBrush, QColor, QIcon
from PyQt5.QtWidgets import QMainWindow, QDialog, QPushButton, QLineEdit, QLabel, QMenu, QGridLayout, QTableView, QHeaderView, QAbstractItemView, QTreeView, QSystemTrayIcon, QMessageBox

#################################################
# Task describe
#################################################
class CTask:
    #--------------------------------------------
    # Init new task
    def __init__(self, task_id, task_name, parent):
        self.task_id   = task_id
        self.task_name = task_name
        self.start     = 0
        self.end       = 0
        self.jobs      = []
        self.parent    = parent
        self.spend     = 0

    #--------------------------------------------
    # Return jobs count for this task
    def jobsCount(self):
        return len(self.jobs)

    #--------------------------------------------
    # Return job row index
    def jobRow(self, job):
        return self.jobs.index(job);

    #--------------------------------------------
    # Add new job for this task
    def addJob(self, child):
        self.spend += child.end - child.start
        self.jobs.append(child)

    #--------------------------------------------
    # Remove job for this task
    def remJob(self, child):
        self.spend -= child.end - child.start
        self.jobs.remove(child)

    #--------------------------------------------
    # Get job by row number
    def getJob(self, row):
        return self.jobs[row]

    #--------------------------------------------
    # Return time of start
    def getTaskStart(self):
        return time.ctime(self.start)

    #--------------------------------------------
    # Return time of end
    def getTaskEnd(self):
        return time.ctime(self.end)

    #--------------------------------------------
    # Return parent job
    def getParent(self):
        return self.parent

    #--------------------------------------------
    # Get total spend time for task
    def getSpend(self):
        return self.spend

    #--------------------------------------------
    # Return task name
    def getTaskName(self):
        return self.task_name

#################################################
# data storage class
#################################################
class CDataStorage:
    #--------------------------------------------
    # Init class. Create connection to DB, create task datebase
    def __init__(self, basename='data.db'):
        self.conection = sqlite3.connect(basename)
        try:
            cursor = self.conection.cursor()
            cursor.execute('CREATE TABLE tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, taskname VARCHAR(100))')
            self.conection.commit()
        except:
            pass

    #--------------------------------------------
    # Generator for tasks list
    def tasksList(self):
        cursor = self.conection.cursor()
        cursor.execute('SELECT * from tasks')
        for task_id, task_name in cursor:
            yield task_id, task_name

    #--------------------------------------------
    # Generator for jobs list
    def jobsList(self, task_id):
        cursor = self.conection.cursor()
        cursor.execute('SELECT * from task_' + str(task_id))
        for job_id, start, end in cursor:
            yield job_id, start, end

    #--------------------------------------------
    # Add new task, return its unique ID
    def addTask(self, task_name):
        cursor = self.conection.cursor()
        cursor.execute('INSERT INTO tasks (taskname) VALUES(\'' + task_name + '\')');
        task_id = cursor.lastrowid
        cursor.execute('CREATE TABLE task_' + str(task_id) + '(job_id INTEGER PRIMARY KEY AUTOINCREMENT, start VARCHAR(32), end VARCHAR(32))')
        self.conection.commit()
        return task_id

    #--------------------------------------------
    # Add new job for task with task_id
    def addJob(self, task_id, start, end):
        cursor = self.conection.cursor()
        cursor.execute('INSERT INTO task_' + str(task_id) + ' (start, end) VALUES(\'' + str(start) + '\', \'' + str(end) + '\')')
        self.conection.commit()

    #--------------------------------------------
    # Remove task by its ID
    def remTask(self, task_id):
        cursor = self.conection.cursor()
        cursor.execute('DROP TABLE task_' + str(task_id))
        cursor.execute('DELETE FROM tasks WHERE task_id=' + str(task_id))
        self.conection.commit()

    #--------------------------------------------
    # Remove job by its task_id and job_id
    def remJob(self, task_id, job_id):
        cursor = self.conection.cursor()
        cursor.execute('DELETE FROM task_' + str(task_id) +  ' WHERE job_id=' + str(job_id))
        self.conection.commit()


#################################################
# data model class
#################################################
class CDataModel(QAbstractItemModel):
    #--------------------------------------------
    # Init class, fill task/jobs tree
    def __init__(self):
        super().__init__()
        self.taskList     = []
        self.active_index = -1
        self.active_time  = 0
        self.db = CDataStorage()

        for task_id, task_name in self.db.tasksList():
            task = CTask(task_id, task_name, None)
            self.taskList.append(task)

            for job_id, start, end in self.db.jobsList(task_id):
                job       = CTask(job_id, '', task)
                job.start = int(start)
                job.end   = int(end)
                task.addJob(job)

    #--------------------------------------------
    # Destroy class. Done current job and write to DB
    def __del__(self):
        if self.active_index != -1:
            self.addCurrentJob()


    #--------------------------------------------
    # Create model index for selected element
    def index(self, row, col, parent=QModelIndex()):
        if not self.hasIndex(row, col, parent):
            return QModelIndex()

        # top level item (task)
        if  not parent.isValid():           
            return self.createIndex(row, col, self.taskList[row])

        # second level item (job)
        item = parent.internalPointer().getJob(row)
        return self.createIndex(row, col, item)

    #--------------------------------------------
    # Return parent for selected model index
    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        item = index.internalPointer().getParent()
        if item == None:
            return QModelIndex()
        else:
            return self.createIndex(index.row(), index.column(), item)

    #--------------------------------------------
    # Return row count
    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return len(self.taskList)
        else:
            return parent.internalPointer().jobsCount()

    #--------------------------------------------
    # Return column count - always 3 (task_name, start, end)
    def columnCount(self, parent=QModelIndex()):
        return 3

    #--------------------------------------------
    # Get data by index
    def data(self, model_index, role=Qt.DisplayRole):
        task   = model_index.internalPointer()
        parent = task.getParent()

        if role == Qt.BackgroundRole and parent == None and model_index.row() == self.active_index:
            return QVariant(QBrush(QColor(0,255,0)))

        if role != Qt.DisplayRole or not model_index.isValid():
            return QVariant()

        column = model_index.column()
        if parent:
            if column == 0:
                return ''
            elif column == 1:
                return task.getTaskStart()
            else:
                return task.getTaskEnd()
        else:
            if column == 0:
                return task.task_name
            elif column == 1:
                spend  = task.getSpend()
                if self.active_index == model_index.row():
                    spend += round(time.time()) - self.active_time
                days   = round(spend/(60*60*24)-0.5)
                hours  = round((spend - days*(60*60*24))/(60*60)-0.5)
                minuts = round((spend - days*(60*60*24) - hours*(60*60))/60-0.5)
                second = round((spend - days*(60*60*24) - hours*(60*60) - minuts*60))
                return 'Spend {0} days, {1} hours {2} minuts {3} sec'.format(days, hours, minuts, second)
            else:
                return ''

    #--------------------------------------------
    # Add new task to data model, update DB and current view
    def addTask(self, task_name):
        if task_name == '':
            return
        task_id = self.db.addTask(task_name)
        task = CTask(task_id, task_name, None)

        self.beginInsertRows(QModelIndex(), len(self.taskList), len(self.taskList))
        self.taskList.append(task)
        self.endInsertRows()
        self.dataChanged.emit(self.createIndex( len(self.taskList), 0, task),  
                              self.createIndex( len(self.taskList), 2, task))

    #--------------------------------------------
    # Done job, add info to DB
    def addCurrentJob(self):
        task = self.taskList[self.active_index]
        self.db.addJob(task.task_id, self.active_time, round(time.time()) )

        job       = CTask(task.task_id, '', task)
        job.start = self.active_time
        job.end   = round(time.time())

        self.beginInsertRows(self.createIndex(self.active_index, 0, task) , task.jobsCount(), task.jobsCount())
        task.addJob(job)
        self.endInsertRows()
        self.dataChanged.emit(self.createIndex(self.active_index, 0, task),  
                              self.createIndex(self.active_index, 2, task))

    #--------------------------------------------
    # Remove task from list
    def remTask(self, task):
        task_row = self.taskList.index(task)
        self.db.remTask(task.task_id)

        self.beginRemoveRows(QModelIndex(), task_row, task_row)
        self.taskList.remove(task)
        self.endRemoveRows()
        self.dataChanged.emit(self.createIndex(task_row, 0, task),  
                              self.createIndex(task_row, 2, task))

    #--------------------------------------------
    # Remove job from list
    def remJob(self, job, idx):
        parent = job.getParent()
        job_row = parent.jobRow(job)
        self.db.remJob(parent.task_id, job.task_id)

        #self.beginRemoveRows(QModelIndex(), 0, parent.jobsCount())
        self.beginRemoveRows(QModelIndex(), job_row, job_row)
        parent.remJob(job)
        self.endRemoveRows()
        self.dataChanged.emit(self.createIndex(job_row, 0, job),  
                              self.createIndex(job_row, 2, job))
    #--------------------------------------------
    # Remove element from data model
    def removeByIndex(self, idx):
        item = idx.internalPointer()
        if not item.getParent():
            if self.active_index == idx.row():
                self.active_index = -1
            self.remTask(item)
        else:
            self.remJob(item, idx)

    #--------------------------------------------
    def setActiveJob(self, index):
        if index.internalPointer().getParent() != None:
            return

        if self.active_index != -1:
            self.addCurrentJob()

        self.dataChanged.emit( self.index(self.active_index, 0),  self.index(self.active_index, 2))
        self.active_time = round(time.time())
        self.active_index = index.row()

    #--------------------------------------------
    def setDeactiveJob(self, index):
        if index.internalPointer().getParent() != None:
            return
        if self.active_index == index.row():
            self.addCurrentJob()
            self.active_index = -1

#################################################
# 'Add new task' window
#################################################
class CAddNewTaskWindow (QDialog):
    #--------------------------------------------
    def __init__(self):
        super().__init__()
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle(self.tr('New task'))

        self.tsk_label     = QLabel(self.tr('Task name:'))
        self.tsk_edit      = QLineEdit()
        self.ok_button     = QPushButton(self.tr('Add'))
        self.cancel_button = QPushButton(self.tr('Cancel'))

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.tsk_label,     0, 0, 1, 1)
        self.layout.addWidget(self.tsk_edit,      0, 1, 1, 3)
        self.layout.addWidget(self.ok_button,     1, 0, 1, 2)
        self.layout.addWidget(self.cancel_button, 1, 3, 1, 2)

        self.ok_button.pressed.connect(self.ok_press)
        self.cancel_button.pressed.connect(self.cancel_press)

    #--------------------------------------------
    @staticmethod
    def process():
        new_task = CAddNewTaskWindow()
        new_task.exec()
        return new_task.result

    #--------------------------------------------
    def ok_press(self):
        self.result = self.tsk_edit.text()
        self.close()

    #--------------------------------------------
    def cancel_press(self):
        self.result = ''
        self.close()


class CTaskTreeView(QTreeView):
    #--------------------------------------------
    def __init__(self):
        super().__init__()
        self.model = CDataModel()
        self.setModel(self.model)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.setColumnWidth(0, 500)
        self.setColumnWidth(1, 250)
        self.setColumnWidth(2, 250)

        self.menu = QMenu(self)
        activateTaskAction   = self.menu.addAction('Activate')
        deactivateTaskAction = self.menu.addAction('Deactivate')
        self.menu.addSeparator()
        newTaskAction = self.menu.addAction('New task')
        remTaskAction = self.menu.addAction('Remove')
        self.menu.setContextMenuPolicy(Qt.CustomContextMenu)
        
        self.customContextMenuRequested.connect(self.popupShow)
        newTaskAction.triggered.connect(self.newTask)
        remTaskAction.triggered.connect(self.remTask)
        activateTaskAction.triggered.connect(self.activateTask)
        deactivateTaskAction.triggered.connect(self.deactivateTask)

    #--------------------------------------------
    # Show popup menu
    def popupShow(self, point):
        self.popup_point = point
        self.menu.popup(self.mapToGlobal(self.popup_point))

    #--------------------------------------------
    def newTask(self):
        task_name = CAddNewTaskWindow.process()
        self.model.addTask(task_name)

    #--------------------------------------------
    def remTask(self):
        idx  = self.indexAt(self.popup_point)
        if not idx.isValid():
            return

        item = idx.internalPointer()

        ask = QMessageBox()
        if item.task_name != '':
            ask.setText(self.tr('Realy delete task ') + item.task_name + '?')
        else:
            ask.setText(self.tr('Realy delete job from ') + item.getTaskStart() + ' to ' + item.getTaskEnd() + '?')
        ask.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ask.setDefaultButton(QMessageBox.No)
        if ask.exec() == QMessageBox.Yes:
            self.model.removeByIndex(idx)

    #--------------------------------------------
    def activateTask(self):
        idx  = self.indexAt(self.popup_point)
        if (idx.isValid()):
            self.model.setActiveJob(idx)

    #--------------------------------------------
    def deactivateTask(self):
        idx  = self.indexAt(self.popup_point)
        if (idx.isValid()):
            self.model.setDeactiveJob(idx)


#************************************************
# main window class
class CMainWindow(QMainWindow): 
  #--------------------------------------------
    # default constructor
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr('Task manager'))
        self.taskView = CTaskTreeView()
        self.setCentralWidget(self.taskView)
        self.resize(1050, 400)
        self.show()

        menu = QMenu(self)
        showAction = menu.addAction('Show/Hide')
        exitAction = menu.addAction('Exit')

        self.stIcon = QSystemTrayIcon()
        self.stIcon.setIcon(QIcon('process-stop.png'))
        self.stIcon.setContextMenu(menu)
        self.stIcon.show()

        showAction.triggered.connect(self.showHideHandler)
        exitAction.triggered.connect(self.exitHandler)
        

    #--------------------------------------------
    def closeEvent(self, event):
        if not hasattr(self, 'appClose'):
            event.ignore()
            self.setVisible(False)

    #--------------------------------------------
    def showHideHandler(self):
        self.setVisible(not self.isVisible())

    #--------------------------------------------
    def exitHandler(self):
        self.appClose = True
        self.close()

        
