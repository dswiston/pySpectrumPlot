#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 30 20:50:15 2025

@author: dave
"""
# Import libraries
import numpy
import time
import iio
import math
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets
import numpy as np


# https://ez.analog.com/linux-software-drivers/f/q-a/117300/how-to-set-number-of-buffers-in-iio-py
# https://ez.analog.com/adieducation/university-program/f/q-a/77879/adalm-pluto-sample-rate
# https://wiki.analog.com/university/tools/pluto/controlling_the_transceiver_and_transferring_data
# https://wiki.analog.com/resources/tools-software/linux-software/libiio_tips_tricks
# https://gitlab.com/tfcollins/plutosdr_scripts/-/blob/master/pluto.py?ref_type=heads
# https://www.bing.com/search?q=travis+collins+pluto+example+script+example&qs=GS&pq=%22travis+collins+pluto+example+script%22&sk=HS1GS2&sc=12-37&cvid=B0C269308B5849F494F917B31BFAAB1F&FORM=QBRE&sp=4&lq=0&dayref=1
# https://www.analog.com/en/resources/technical-books/software-defined-radio-for-engineers.html


class Sdr():
    def __init__(self,sampRate,buffSize,rfBandwidth,freqSpacing):
        super().__init__()
        # Setup SDR objects
        self.ctx = iio.Context('ip:192.168.2.1');
        self.ctrl = self.ctx.find_device("ad9361-phy");
        self.txdac = self.ctx.find_device("cf-ad9361-dds-core-lpc");
        self.rxadc = self.ctx.find_device("cf-ad9361-lpc");
        self.rxLo = self.ctrl.channels[0];
        self.txLo = self.ctrl.channels[1];     
        self.rxPath = self.ctrl.channels[4];
        self.txPath = self.ctrl.channels[5];
        
        # Setup SDR objects
        self.ctx = iio.Context('ip:192.168.2.1');
        self.ctrl = self.ctx.find_device("ad9361-phy");
        self.txdac = self.ctx.find_device("cf-ad9361-dds-core-lpc");
        self.rxadc = self.ctx.find_device("cf-ad9361-lpc");
        self.rxLo = self.ctrl.channels[0];
        self.txLo = self.ctrl.channels[1];     
        self.rxPath = self.ctrl.channels[4];
        self.txPath = self.ctrl.channels[5];
        
        # Configure properties
        
        self.numRxBuffers = 1;    # If we don't set this to one, will waste time reading multiple
                                  # buffers after retuning the LO 
        self.rfBandwidth = rfBandwidth;
        self.sampRate = sampRate;
        # Set to one since we'll be hopping the LO around a lot and if we don't
        # we'll need to empty multiple buffers before data from the new LO #
        # setting shows up, very inefficient
        self.rxadc.set_kernel_buffers_count(self.numRxBuffers);
        self.rxPath.attrs["rf_bandwidth"].value = str(int(self.rfBandwidth));
        self.rxPath.attrs["sampling_frequency"].value = str(int(self.sampRate));
        self.rxPath.attrs['gain_control_mode'].value = 'manual';
        self.rxPath.attrs['hardwaregain'].value = '60'
        
        # Enable rx channel
        self.rxadc.channels[0].enabled = True;
        self.rxadc.channels[1].enabled = True; # one for I, one for Q
        
        # Create IQ buffer
        self.freqSpacing = freqSpacing;
        self.buffSize = buffSize;
        self.rxBuff = iio.Buffer(self.rxadc, self.buffSize, False);
        
        # Define the frequency vector resulting from taking the FFT of each buffer
        self.freqs = numpy.arange(-self.buffSize/2,self.buffSize/2)*self.sampRate/self.buffSize;

        self.freqPad = self.freqSpacing * 0;   # Don't use the full bandwidth in the collect, assume some analog "fall-off"


class Plt():
    def __init__(self,startFreq,stopFreq,sampRate,buffSize,freqSpacing):
        super().__init__()
        
        # Set waterfall size to keep for persistence
        self.numRows = 128;
        
        # Create initial empty image - scale to -1000 to make it obvious this is empty data
        self.imgBuff = numpy.empty((self.numRows,int(math.ceil((stopFreq-startFreq)/sampRate*buffSize))));

        # Plotting stuff
        self.startFreq = startFreq;
        self.freqSpacing = freqSpacing;
        
        # Create a plot for labels, grid, etc
        self.plot = pg.PlotItem();
        self.plot.setLabel(axis='bottom', text='Frequency (MHz)');
        self.plot.hideAxis(axis='left');
        self.plot.hoverEvent = self.show_tooltip;
        
        # Create an ImageView widget
        self.image = pg.ImageView(view=self.plot);
        
        # Set the hover event callback
        self.image.hoverEvent = self.show_tooltip

        # Set the default image data
        self.image.setImage(self.imgBuff);
        self.image.view.setAspectLocked(False);
        
        # Grab a colormap
        cm = pg.colormap.get('CET-L9') # prepare a linear color map
        
        # setting color map to the image view - pg.colormap.listMaps()
        self.image.setColorMap(cm)
        
        
    def show_tooltip(self, event):
        # Check to make sure this isn't an exit event
        if event.isExit():
            return
        # It isn't, get the position, convert it to the plot's view
        pos = event.pos();
        tmp = self.plot.mapToView(pos);
        # Set the plot's tooltip, round to three decimal places
        self.plot.setToolTip(str(round(tmp.x(),3))+"MHz")



class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.freqSpacing = 500;
        # Define the frequency scanning range
        self.startFreq = 87.5e6;   # FM Radio
        self.stopFreq = 107.5e6;       
        # self.startFreq = 108e6;    # Radar
        # self.stopFreq = 117.975e6;
        # self.startFreq = 174e6;      # VHF Broadcast TV
        # self.stopFreq = 216e6;
        # self.startFreq = 470e6;      # UHF Broadcast TV (trimmed)
        # self.stopFreq = 608e6;
        # self.startFreq = 902e6;    # UHF ISM
        # self.stopFreq = 928e6;

        # self.startFreq = 1088e6;   # ADSB
        # self.stopFreq = 1092e6;
        # self.startFreq = 1028e6;   # ADSB
        # self.stopFreq = 1092e6;
        # self.startFreq = 960e6;    # Radar
        # self.stopFreq = 1164e6;
        # self.startFreq = 1164e6;    # Space
        # self.stopFreq = 1300e6;
        # self.startFreq = 1300e6;   # Radar
        # self.stopFreq = 1350e6;
        # self.startFreq = 2.4e9;    # 2.4GHz ISM
        # self.stopFreq = 2.4835e9;        
        
        # Define min and max rates to allow
        maxRate = 56000000.0;
        minRate =  3000000.0;
        
        # Attempt to derive the most efficient setting while not violating limits
        self.rfBandwidth = max(min(maxRate,(self.stopFreq-self.startFreq)*1.01),minRate);
        self.sampRate = self.rfBandwidth;
        self.buffSize = int(self.sampRate / self.freqSpacing);
        
        # Create plot window
        self.plt = Plt(self.startFreq,self.stopFreq,self.sampRate,self.buffSize,self.freqSpacing);
        self.setCentralWidget(self.plt.image);
        self.fps = 0;
        self.updateTime = time.time();
        
        # Create the data thread
        self.dataAcq = DataAcquisition(self.startFreq,self.stopFreq,self.sampRate,self.buffSize,self.rfBandwidth,self.freqSpacing);
        # Connect the data thread to the function that updates the plot
        self.dataAcq.dataSignal.connect(self.UpdatePlot);
        # Start the data thread
        self.dataAcq.start();
        
    def closeEvent(self, event):
        """Handle cleanup when the window is closed."""
        print("Closing application...")
        self.dataAcq.stop();  # Gracefully stop the thread
        self.dataAcq.wait();  # Wait for the thread to finish
        event.accept();

    
    def UpdatePlot(self,magData):

      # Roll (circ shift) the buffer in anticipation of inserting new data
      # This goes "bottom up" - if you want top down change the roll to +1 and place the new data
      # in to the first element
      self.plt.imgBuff = numpy.roll(self.plt.imgBuff,-1,axis=0);
      # Replace old data
      self.plt.imgBuff[-1,] = magData;
                  
      # Update the image data
      self.plt.image.setImage(self.plt.imgBuff.T, levels=(-90, -40), scale=(self.plt.freqSpacing/1e6,1), pos=(self.plt.startFreq/1e6,0)) #, autoLevels=False);
      tmpTime = time.time();
      self.fps = self.fps * 0.5 + 1/(tmpTime-self.updateTime);
      self.updateTime = tmpTime;
      #print(self.fps);

        
class DataAcquisition(QtCore.QThread):
  
    # Signal to send data to the main thread - object data type b/c we're sending an nparray
    dataSignal = QtCore.pyqtSignal(object); 
    runThread = True;
        
    def __init__(self,startFreq,stopFreq,sampRate,buffSize,rfBandwidth,freqSpacing):
        super().__init__()
        # Create SDR
        self.sdr = Sdr(sampRate,buffSize,rfBandwidth,freqSpacing);
        self.startFreq = startFreq;
        self.stopFreq = stopFreq;
        
    def stop(self):
      self.runThread = False;
      
    def run(self):

      numCols = int(math.ceil((self.stopFreq-self.startFreq)/self.sdr.sampRate*self.sdr.buffSize));
      fftData = np.zeros((numCols,),dtype=np.complex64);
      magData = np.zeros((numCols,),dtype=np.complex64);

      while self.runThread:
        
        tic = time.time();
        freqTune = self.startFreq+self.sdr.sampRate/2;
        
        while freqTune <= self.stopFreq+self.sdr.sampRate/2:

           # Tune the LO
           self.sdr.rxLo.attrs["frequency"].value = str(int(freqTune));
             
           # print(freqTune);
           # print(self.rxLo.attrs["frequency"].value);
           
           # Fill and grab a buffers worth of data
           self.sdr.rxBuff.refill();
           tmpData = np.frombuffer(self.sdr.rxBuff.read(),dtype=np.int16) / 2**12;
           data = np.empty((int(len(tmpData)/2)), dtype=np.complex64);
           data.real = tmpData[::2];
           data.imag = tmpData[1::2];
           
           # Calculate the frequency spectrum
           tmp = numpy.fft.fft(data)/self.sdr.buffSize;  # Remove FFT gain by scaling by buffer size
           tmp = numpy.fft.fftshift(tmp);            # Shift FFT so zero is in the middle
           
           # Calculate the RF frequencies of each data point
           freqPts = freqTune + self.sdr.freqs;
           freqBins = np.int32((freqPts - self.startFreq) / self.sdr.freqSpacing);
           
           # Determine which frequencies to keep (that are of interest)
           keepNdx = (freqBins >= 0) & (freqBins<numCols);

           # Insert into formal data set that gets converted to an image
           # self.debugData[freqBins[keepNdx]] = freqPts[keepNdx];
           fftData[freqBins[keepNdx]] = tmp[keepNdx];
           
           # Advance the RF frequency tune
           freqTune = freqTune + self.sdr.sampRate - self.sdr.freqPad;
       
        magData = 20*numpy.log10(numpy.abs(fftData));
        magData[np.isinf(magData)] = -100;
        
        # Lame attempt to throttle update rate & smooth out the display
        elapsedTime = time.time()-tic;
        if elapsedTime < 0.025:
          time.sleep(0.025-elapsedTime);
        
        self.dataSignal.emit(magData);

      print("Data thread exiting")
       
       
app = QtWidgets.QApplication([]);

main = MainWindow();
main.show();
app.exec();

