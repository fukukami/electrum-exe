#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys, time, datetime, re, threading
from electrum.i18n import _, set_language
from electrum.util import print_error, print_msg, parse_url
import os.path, json, ast, traceback
import shutil


try:
    import PyQt4
except:
    sys.exit("Error: Could not import PyQt4 on Linux systems, you may try 'sudo apt-get install python-qt4'")

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore

from electrum import WalletStorage, Wallet
from electrum.i18n import _
from electrum.bitcoin import MIN_RELAY_TX_FEE

try:
    import icons_rc
except:
    sys.exit("Error: Could not import icons_rc.py, please generate it with: 'pyrcc4 icons.qrc -o gui/gui_classic/icons_rc.py'")

from qt_util import *
from main_window import ElectrumWindow


class Timer(QtCore.QThread):
    def run(self):
        while True:
            self.emit(QtCore.SIGNAL('timersignal'))
            time.sleep(0.5)

class OpenFileEventFilter(QObject):
    def __init__(self, windows):
        self.windows = windows
        super(OpenFileEventFilter, self).__init__()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.FileOpen:
            if len(self.windows) >= 1:
                self.windows[0].set_url(event.url().toString())
                return True
        return False


class ElectrumGui:

    def __init__(self, config, network, app=None):
        self.network = network
        self.config = config
        self.windows = []
        self.efilter = OpenFileEventFilter(self.windows)
        if app is None:
            self.app = QApplication(sys.argv)
        self.app.installEventFilter(self.efilter)

    def expand(self):
        """Hide the lite mode window and show pro-mode."""
        self.config.set_key('lite_mode', False, True)
        self.mini.hide()
        self.expert.show()

    def minimize(self, wallet, expert, url):
        import lite_window
        actuator = lite_window.MiniActuator(self.config, wallet)
        # Should probably not modify the current path but instead
        # change the behaviour of rsrc(...)
        old_path = QDir.currentPath()
        actuator.load_theme()

        self.mini = lite_window.MiniWindow(actuator, self.expand, self.config)
        driver = lite_window.MiniDriver(wallet, self.mini)

        # Reset path back to original value now that loading the GUI
        # is completed.
        QDir.setCurrent(old_path)
        
        if url:
            payto, amount, label, message, signature, identity, url = parse_url(url)
            self.mini.set_payment_fields(payto, amount)

        self.expert = expert

    def check_qt_version(self):
        qtVersion = qVersion()
        if not(int(qtVersion[0]) >= 4 and int(qtVersion[2]) >= 7):
            app = QApplication(sys.argv)
            QMessageBox.warning(None,"Could not start Lite GUI.", "Electrum was unable to load the 'Lite GUI' because it needs Qt version >= 4.7.\nChanging your config to use the 'Classic' GUI")
            self.config.set_key('lite_mode', False, True)
            sys.exit(0)

    def main(self, url):

        storage = WalletStorage(self.config)
        if not storage.file_exists:
            import installwizard
            wizard = installwizard.InstallWizard(self.config, self.network, storage)
            wallet = wizard.run()
            if not wallet: 
                exit()
        else:
            wallet = Wallet(storage)

        wallet.start_threads(self.network)

        s = Timer()
        s.start()
            
        w = ElectrumWindow(self.config, self.network)
        w.load_wallet(wallet)

        self.windows.append(w)
        if url: w.set_url(url)
        w.app = self.app
        w.connect_slots(s)
        w.update_wallet()

        if self.config.get('lite_mode'):
            self.check_qt_version()
            self.minimize(wallet, w, url)
        else:
            w.show()

        self.app.exec_()

        wallet.stop_threads()


