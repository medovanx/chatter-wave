from PyQt5.QtCore import pyqtSignal, QObject


class SignalHandler(QObject):
    """Class to handle signals across threads"""
    message_received = pyqtSignal(dict)
    connection_error = pyqtSignal(str)
    user_list_updated = pyqtSignal(list)
