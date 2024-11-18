"""
Last update: 16/09/2024


Created on Fri May 03 08:23:17 2021
Aragon Photonics Labs. S.L.U.

%%% This document is a strictly confidential communication to and solely %%
%%% for the use of the individual or entity recipient and may not be     %%
%%% reproduced or circulated without Aragon Photonics Labs S.L.U. prior  %%
%%% written consent. If you are not the intended recipient, you may not  %%
%%% disclose or use the information in this documentation in any way.    %%

"""

import numpy as np
import concurrent.futures

def Load_2D_Data_bin(fullPath: str) -> list:
    """

    :parameter fullPath: path of bin file

    :return:
    """
    fileID = open(fullPath, "rb")
    fileID.seek(0)
    dataType = np.float64
    "np.dtype('<f8')"

    # Get the FileHeader; The first Position is the FileHeader Size
    headersize = np.fromfile(fileID, dtype=dataType, count=1)
    fHeaderSize = int(headersize[0])
    header_data = np.fromfile(fileID, dtype=dataType, count=(fHeaderSize-1))
    header = np.hstack((headersize, header_data))

    raw_file = np.fromfile(fileID, dtype=dataType)
    fileID.close()

    "-- Get datastructure variables from the FileHeader"
    "Number of points monitored along the fiber"
    mK_to_Strain = 10

    " File type is HDAS_2Dmap_Strain"
    if header[101] == 2:
        N_processed_Points =  int(header[14] - header[12])

    "Build 2D Data Matrix"
    N_Time_Samples = int(len(raw_file) / N_processed_Points)
    
    
    try:
        TracesMatrix = raw_file.reshape((N_Time_Samples, N_processed_Points))
        TracesMatrix = TracesMatrix.transpose()
    
    except ValueError:
        TracesMatrix = None
    del raw_file
    TracesMatrix = TracesMatrix * mK_to_Strain

    return [TracesMatrix, header]

if __name__=="__main__":
    path = "./DAS/2021/11/20"
    filename = "2021_11_20_00h00m37s_HDAS_2Dmap_Strain.bin"
    fullPath = "%s/%s" % (path, filename)
    [dd, header] = Load_2D_Data_bin(fullPath)
    
    sps = slice(10, 15)


    print(dd.shape, header.shape)
    print(dd[sps].shape, header.shape)

    print(header)

