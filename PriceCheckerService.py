import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import os
import sys
import time

class VictozaPriceTrackerService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'VictozaPriceTrackerService'
    _svc_display_name_ = 'Victoza Price Tracker Service'
    _svc_description_ = 'A service to track the price of Victoza.'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_alive = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_alive = False

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from main import main
        while self.is_alive:
            main()
            time.sleep(60)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(VictozaPriceTrackerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(VictozaPriceTrackerService)