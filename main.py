import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QDialog
import logging
import asyncio
from Ui.MainWindow import Ui_MainWindow
from Ui.Dialog import Ui_Dialog
from decoder import decoder_11, decoder_10
from bleak import BleakClient
import time
import threading
from PyQt5.QtCore import pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QIcon
from bleak import BleakScanner
import pyqtgraph as pg
from datetime import datetime


ADDRESS = ""

class DialogWindow(QDialog, Ui_Dialog):
    newdata = pyqtSignal(object) # 创建信号
    # stop_thread = pyqtSignal()
    def __init__(self, parent=None):
        super(DialogWindow, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('BlueTooth-DMM Monitor')
        #BLE Devices
        self.logger = logging.getLogger(__name__)
        self.t = []
        self.digi = []
        self.char = []
        self.lcdNumber.setStyleSheet("line-height:200%")
        self.lcdNumber.setDigitCount(8)
        self.pushButton_start.clicked.connect(self.startThread)
        self.pushButton_stop.clicked.connect(self.stopThread)


        # Add pyqtgraph to qtwidget
        self.plot_plt = pg.PlotWidget()
        self.plot_plt.showGrid(x=True,y=True)
        self.graph_layout.addWidget(self.plot_plt)




#    def update_progressbar(self, p_int):
#        self.progressBar.setValue(p_int)




        # plot speed

        #self.comboBox.currentIndexChanged.connect(self.selectionchange)
        self.comboBox.setCurrentIndex(1) 
        self.comboBox_currentIndex = 1
        self.checkBox_isChecked = self.checkBox.isChecked()
        self.a = 0
        self.plotspeed_param = 11

        #plot clear
        self.b = 0
        self.plotclear_param = 10000

        self.newdata.connect(self.plot)

        self.data_list = []

        # stopThread
        self.stop_collect = 0

    def stopThread(self):
        self.stop_collect = 1
        self.pushButton_start.setEnabled(True)
        print ('Stop the thread...')
        
    def closeEvent(self, event):
        self.stopThread()
        pass

    # getdata
    def startThread(self):
        '''
        这里使用python的threading.Thread构造线程，并将线程设置为守护线程，这样
        主线程退出后守护线程也会跟着销毁
        Here we use python's threading.Thread to construct a thread, and set the thread as a daemon thread, 
        so that the daemon thread will also be destroyed after the main thread exits.
        '''
        print('Daemon thread starts')
        self.pushButton_start.setEnabled(False)
        print('Start listening to Bluetooth')
        thread = threading.Thread(target=self.getdata)
        thread.setDaemon(True) # 守护线程

        thread.start() # 启动线程
    # mian loop to get data
    async def data(self, ADDRESS):
        try:
            async with BleakClient(ADDRESS) as client:
                self.logger.info(f"Connected: {client.is_connected}")
                try:
                    print('now')
                    self.stop_collect = 0
                    while self.stop_collect == 0 : 
                        
                        value = bytes(await client.read_gatt_char(8, use_cached=1))
                        ## print(value.hex())
                        ## 11 Byte DMM
                        if len(value.hex()) == 22:
                            A = decoder_11.printdigit(decoder_11.decode(value.hex()))
                            # list to str
                            B = ' '.join(decoder_11.printchar(decoder_11.decode(value.hex())))
                        ## 10 Byte DMM
                        elif len(value.hex()) == 20:
                            A = decoder_10.printdigit(decoder_10.decode(value.hex()))
                            # list to str
                            B = ' '.join(decoder_10.printchar(decoder_10.decode(value.hex())))

                        #self.t.append(time.time())
                        now = datetime.now()
                        self.t = now.strftime('%Y-%m-%d %H:%M:%S')
                        #self.t = time.asctime(time.localtime(time.time()))
                        
                        print(A)
                        print(B)
                        self.digi = float(A)
                        self.char = str(B)
                        signal = (self.t,(self.digi, self.char))
                        self.newdata.emit(signal)
                        print(self.t)
                        #self.lcdNumber.display(signal[1][0])
                        #self.label_2.setText(signal[1][1])
                        self.newdata.emit(signal)
                        time.sleep(1/3)
                    # when stop button be pushed, clear connection
                    self.lcdNumber.display(0)
                    self.plot_plt.clear()
                    self.data_list=[]
                    try:
                        f.close()
                    except:
                        print("No file opened")
                    print("Closed successfully")
                except:
                    print('Connection Closed')
                    self.pushButton_start.setEnabled(True)
        except:
            self.pushButton.start.setEnabled(True)
            print('Failed to asyn '+ADDRESS)
    

    def getdata(self):
        try:
            print(ADDRESS)
            asyncio.run(self.data(sys.argv[1] if len(sys.argv) == 2 else ADDRESS))
        except:
            print(ADDRESS)
            print("No device found")

    # real time plot
    def plot(self,signal):
        # combobox for different speed
        self.comboBox_currentIndex = self.comboBox.currentIndex()
        if self.comboBox_currentIndex == 1:
            self.plotspeed_param = 11
        elif self.comboBox_currentIndex == 0:
            self.plotspeed_param = 1
        elif self.comboBox_currentIndex == 2:
            self.plotspeed_param = 23

        # real time lcd and label
        self.lcdNumber.display(signal[1][0])
        self.label_2.setText(signal[1][1])
        # pyqtgraph with different speed
        if self.a > self.plotspeed_param:
            self.data_list.append(signal[1][0])
            self.plot_plt.plot().setData(self.data_list,pen='w')
            self.a = 0
            self.b = self.b + 1
        self.a = self.a + 1
        # Clear the pyqtgraph screen regularly
        if self.b > self.plotclear_param:
            self.plot_plt.clear()
            self.data_list=[]
            self.b = 0
        # write to file, with speed control and checkbox control
        if self.a > self.plotspeed_param:
            now = datetime.now()
            if self.checkBox_isChecked != self.checkBox.isChecked():
                if self.checkBox.isChecked() == True:
                    f = open(now.strftime('%Y-%m-%d')+'.txt',mode = 'a', encoding='utf-8')
                    f.write(str(signal[0])+"   "+str(signal[1][0])+" "+signal[1][1]+"\n")
                elif self.checkBox.isChecked() == False:
                    f.close()
            else:
                if self.checkBox.isChecked() == True:
                    f.write(str(signal[0])+"   "+str(signal[1][0])+" "+signal[1][1]+"\n")
                #elif self.checkBox.isChecked() == False:
                    #f.close()





class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    search_complete = pyqtSignal(object) # create signal
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('BlueTooth-DMM Client')
        self.setWindowIcon(QIcon('Logo.png'))
        self.count = 0

###BLE Devices Below
        self.logger = logging.getLogger(__name__)


        self.devices = []
        self.pushButton_search.clicked.connect(self.startThread_devices)
        self.progressBar.setValue(0)
        self.search_complete.connect(self.searching)
        #self.pushButton_search.clicked.connect(self.searching)
        self.listWidget.itemClicked.connect(self.change_address)

        self.pushButton.clicked.connect(self.open_dialog)

        self.actionAbout.triggered.connect(self.open_about)

    def open_about(self):
        QMessageBox.about(self,'About',
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">BLE_DMM_Client v1.0</span></p>\n"
        "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Release page: </span></p>\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"https://github.com/840922704/BLE_DMM_Client\"><span style=\" font-size:8pt; text-decoration: underline; color:#0000ff;\">https://github.com/840922704/BLE_DMM_Client</span></a></p>\n")
###BLE Devices Above


    def open_dialog(self):
        dialog = DialogWindow(self)
        dialog.show()
        dialog.label.setText("Address: "+ADDRESS)

#        self.thread = RunThread(self.count)
#        self.count += 1
#        self.thread.update_pb.connect(dialog.update_progressbar)
#        self.thread.update_pb.connect(dialog.startThread)

#        self.thread.start()

## BLE Devices Below

    def startThread_devices(self):
        '''
        daemon thread
        '''
        print('Searching Bluetooth devices')
        thread = threading.Thread(target=self.search_devices_2)
        thread.setDaemon(True) # 守护线程
        thread.start() # 启动线程
    def search_devices_2(self):
        asyncio.run(self.search_devices())
        
    async def search_devices(self):
        signal = 0
        self.search_complete.emit(signal)

        self.devices = []
        devices = await BleakScanner.discover()
        self.listWidget.clear()

        for d in devices:
            self.listWidget.addItem(str(d))
            print(d)
        signal = 100
        self.search_complete.emit(signal)
    # progressbar flash
    def searching (self,signal):
        if signal == 0:
            self.progressBar.setRange(0,0)
        if signal == 100:
            print("100")
            self.progressBar.setRange(0,100)
            self.progressBar.setValue(100)
        #for a in range(1,101,1):
        #    self.progressBar.setValue(a)
        #    time.sleep(0.05)
    def change_address(self, item):
        global ADDRESS
        ADDRESS = item.text().split(": ")[0]
        print(ADDRESS)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    f = QFont("Arial",12);
    app.setFont(f);
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
