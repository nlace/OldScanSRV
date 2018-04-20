# OldScanSRV

This is a simple python script for use on a Raspberry Pi 3 to extend the functionality of a fujitsu fi-5750Cdj.

To function, it requires the user to compile a current copy of sane-backends, which will require libjpeg and libusb. (if you don't compile with libjpeg you will get stuck with .tif files)

Once finished, the connection string will need to be added to the script. 


## To Do

Add gpio scan button, so the web interface doesn't need to be used to start the scan job. 

