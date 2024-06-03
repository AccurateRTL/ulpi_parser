#!/usr/bin/env python3

from __future__ import print_function

import sys
from pprint import PrettyPrinter

import vcdvcd
from vcdvcd import VCDVCD
from vcdvcd import binary_string_to_hex

PRINT_RXPACKET_DATA=0
PRINT_RXCMD=0

# Декодируем PID передаваемых пакетов
def decode_pid(pid):
  if pid==1:
     return 'OUT'
  if pid==9:
     return 'IN'
  if pid==5:
     return 'SOF'
  if pid==0xD:
     return 'SETUP'
  if pid==0x2:
     return 'ACK'  
  if pid==0xA:
     return 'NAK'  
  if pid==0x6:
     return 'NYET'  
  if pid==0xE:
     return 'STALL'  


# Декодируем PID полученных пакетов
def decode_rx_pid(pid):
  if pid==0xC3:
     return 'DATA0'
  if pid==0x4B:
     return 'DATA1'
  if pid==0x87:
     return 'DATA2'
  if pid==0xD2:
     return 'ACK'
  if pid==0x5A:
     return 'NACK'
  if pid==0x96:
     return 'NYET'
  if pid==0x1E:
     return 'NYET'


# Разбираем TXCMD
def parse_tx_cmd(data_sig, nxt_sig, stp_sig, t):
  cur_data = int(binary_string_to_hex(data_sig[t]),16)
  tx_cmd_word = cur_data
  ulpi_cmd = cur_data & 0xC0
  ulpi_cmd_params = cur_data & 0x3f
  t_start = t;
  ulpi_cmd_data = []
# Ждем подтверждения приема команды
  while(nxt_sig[t]=='0'): 
    t+=1
  t+=1
# Сохраняем данные команды
  while(stp_sig[t]=='0'):
    if nxt_sig[t]=='1': 
      cur_data = int(binary_string_to_hex(data_sig[t]),16)
      ulpi_cmd_data.append(cur_data)     
    t+=1
  
  if (ulpi_cmd==0x40):
    print("%d-%d: %x TX_CMD (Transmit, PID %x %s)" % (t_start, t, tx_cmd_word, ulpi_cmd_params, decode_pid(ulpi_cmd_params & 0xf)), ulpi_cmd_data)
  if (ulpi_cmd==0x80):
    print("%d-%d: %x TX_CMD (RegWrite, Addr %x)" % (t_start, t, tx_cmd_word, ulpi_cmd_params))
  if (ulpi_cmd==0xC0):
    print("%d-%d: %x TX_CMD (RegRead, Addr %x)" % (t_start, t, tx_cmd_word, ulpi_cmd_params))
  return t

# Разбираем RXCMD
def parse_rx_cmd(data_sig, t):
  t_start = t
  # turnaround
  t+=1
  cur_data   = int(binary_string_to_hex(data_sig[t]),16)
  line_state = cur_data & 0x3
  vbus       = cur_data & 0xc
  rx_event   = cur_data & 0x30
  id_flg     = cur_data & 0x40
  alt_int    = cur_data & 0x40
  # turnaround
  t+=1
  if (PRINT_RXCMD==1): print("%d-%d: RX_CMD %x line_st %x VBUS %x rx_event %x id %x" % (t_start, t, cur_data, line_state, vbus, rx_event, id_flg))
  return t

# Разбираем прием пакета
def parse_rx_packet(data_sig, nxt_sig, dir_sig, t):
  t_start = t
  # turnaround
  t+=1
  rx_packet_data = []
  cur_data   = int(binary_string_to_hex(data_sig[t]),16)
  while(dir_sig[t]!='0'):
    if (nxt_sig[t]!='0'):
      cur_data   = int(binary_string_to_hex(data_sig[t]),16)
      rx_packet_data.append(cur_data)
    t+=1     
  t-=1  
  if len(rx_packet_data)>0:
     valid_counter = 1;
     for i in range(len(rx_packet_data)-3):
        if (rx_packet_data[i+1]!=i%256):
            valid_counter = 0
#           print("%d: %d != %d" % (i, rx_packet_data[i+1], i))

     print("%d-%d: RX_PACKET %s len %d %s counter" % (t_start, t, decode_rx_pid(rx_packet_data[0]), len(rx_packet_data), "valid" if valid_counter == 1 else "invalid"))
     if (PRINT_RXPACKET_DATA): 
       print(rx_packet_data)
  else:
     print("%d-%d: RX_PACKET NODATA!" % (t_start, t))
  return t



# Открываем файл с временной диаграммой
if (len(sys.argv) > 1):
    vcd_path = sys.argv[1]
else:
    vcd_path = 'waveform.vcd'
pp = PrettyPrinter()


vcd = VCDVCD(vcd_path)

# Печатаем список сигналов данного файла 
print('# signals')
pp.pprint(vcd.signals)
print()

# Создаем объекты для интересующих нас сигналов
data_sig = vcd['dut.USB_DATAI[7:0]']
nxt_sig  = vcd['dut.USB_NXT_IBUF']
dir_sig  = vcd['dut.USB_OEN']
stp_sig  = vcd['dut.USB_STP_OBUF']

# Печатаем номер последнего отсчета в данном файле
print("endtime: %d" % vcd.endtime)

# Начиная с первого отсчета анализируем шину ULPI
t=1
while t < vcd.endtime:
  cur_data = int(binary_string_to_hex(data_sig[t]),16)
  if (dir_sig[t]=='1'):
    if (nxt_sig[t]=='0'):
      t = parse_rx_cmd(data_sig, t) 
    else:
      t = parse_rx_packet(data_sig, nxt_sig, dir_sig, t)
  else:
    if cur_data!=0:
      t = parse_tx_cmd(data_sig, nxt_sig, stp_sig, t)
  t+=1

