### Interpreter of blood glucose data from Abbot FreeStyle Libre. Spline interpolation and ouptut of 1024 sample wav-file.
### TODO: 1. Cleanup code
### 2. Threading (with QRunnable)!!! Better handling of GUI thread and Model. (Semaphore?) Signals/Slots...
### 3. View inheriting from QWindow instead of QApplication
### 4. Standalone executable (PyInstaller)

from View import View  

View().run_view()
