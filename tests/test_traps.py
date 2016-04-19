from __future__ import print_function

import pytest
from bare68k.consts import *
from bare68k.machine import *

RESET_OPCODE = 0x4e70
NOP_OPCODE = 0x8e71

def test_invalid_trap(mach):
  # callable must be given
  with pytest.raises(TypeError):
    opcode = trap_setup(TRAP_DEFAULT, None)

def test_empty_trap(mach):
  # no trap was set. return event but callback is None
  w_pc(0x100)
  w16(0x100, 0xa000)
  ne = execute(1000)
  assert ne == 1
  ri = get_info()
  print("TRAP", ri)
  assert ri.num_events == 1
  ev = ri.events[0]
  assert ev.ev_type == CPU_EVENT_ALINE_TRAP
  assert ev.addr == 0x100
  assert ev.data is None
  assert ev.handler is None

def test_empty_trap_def_handler(mach):
  def huhu():
    print("huhu")
  event_handlers[CPU_EVENT_ALINE_TRAP] = huhu
  assert event_handlers[CPU_EVENT_ALINE_TRAP] is huhu
  w_pc(0x100)
  w16(0x100, 0xa000)
  ne = execute(1000)
  assert ne == 1
  ri = get_info()
  print("TRAP", ri)
  assert ri.num_events == 1
  ev = ri.events[0]
  assert ev.ev_type == CPU_EVENT_ALINE_TRAP
  assert ev.addr == 0x100
  assert ev.data is None
  assert ev.handler is huhu

def test_default_trap(mach):
  def my_cb():
    print("HUHU")
  opcode = trap_setup(TRAP_DEFAULT, my_cb)
  w_pc(0x100)
  w16(0x100, opcode)
  ne = execute(1000)
  assert ne == 1
  ri = get_info()
  print("TRAP", ri)
  assert ri.num_events == 1
  ev = ri.events[0]
  assert ev.ev_type == CPU_EVENT_ALINE_TRAP
  assert ev.addr == 0x100
  assert ev.data is None
  assert ev.handler == my_cb
  # trigger callback
  ev.handler()
  # finally free trap
  trap_free(opcode)

  # after trap: aline is empty again
  w_pc(0x100)
  w16(0x100, opcode)
  ne = execute(1000)
  assert ne == 1
  ri = get_info()
  print("TRAP", ri)
  assert ri.num_events == 1
  ev = ri.events[0]
  assert ev.ev_type == CPU_EVENT_ALINE_TRAP
  assert ev.addr == 0x100
  assert ev.data is None
  assert ev.handler is None

def test_one_shot_trap(mach):
  def my_cb():
    print("HUHU")
  opcode = trap_setup(TRAP_ONE_SHOT, my_cb)
  w_pc(0x100)
  w16(0x100, opcode)
  ne = execute(1000)
  assert ne == 1
  ri = get_info()
  print("TRAP", ri)
  assert ri.num_events == 1
  ev = ri.events[0]
  assert ev.ev_type == CPU_EVENT_ALINE_TRAP
  assert ev.addr == 0x100
  assert ev.data is None
  assert ev.handler == my_cb
  # trigger callback
  ev.handler()

  # after trap: aline is empty again
  w_pc(0x100)
  w16(0x100, opcode)
  ne = execute(1000)
  assert ne == 1
  ri = get_info()
  print("TRAP", ri)
  assert ri.num_events == 1
  ev = ri.events[0]
  assert ev.ev_type == CPU_EVENT_ALINE_TRAP
  assert ev.addr == 0x100
  assert ev.data is None
  assert ev.handler is None

def test_auto_rts_trap(mach):
  def do():
    # create local callback func to test ref-counting
    def my_cb():
      print("HUHU")
    return trap_setup(TRAP_AUTO_RTS, my_cb)
  opcode = do()

  # setup a stack
  w_sp(0x200)
  w32(0x200, 0x300) # return address on stack
  w16(0x300, RESET_OPCODE)

  # set test code
  w_pc(0x100)
  w16(0x100, opcode)
  ne = execute(1000)
  assert ne == 1
  ri = get_info()
  print("TRAP", ri)
  assert ri.num_events == 1
  ev = ri.events[0]
  assert ev.ev_type == CPU_EVENT_ALINE_TRAP
  assert ev.addr == 0x100
  assert ev.data is None
  assert ev.handler is not None
  # trigger callback
  ev.handler()

  # check next steps: auto rts will be performed
  ne = execute(2)
  assert ne == 1
  ri = get_info()
  print("NEXT", ri)
  assert ri.num_events == 1
  ev = ri.events[0]
  assert ev.ev_type == CPU_EVENT_RESET
  assert ev.addr == 0x302
  assert ev.data is None
  assert ev.handler is None
  # check that stack moved
  assert r_sp() == 0x204

  # finally free trap
  trap_free(opcode)
  # after trap: aline is empty again
  w_pc(0x100)
  w16(0x100, opcode)
  ne = execute(1000)
  assert ne == 1
  ri = get_info()
  print("TRAP", ri)
  assert ri.num_events == 1
  ev = ri.events[0]
  assert ev.ev_type == CPU_EVENT_ALINE_TRAP
  assert ev.addr == 0x100
  assert ev.data is None
  assert ev.handler is None
