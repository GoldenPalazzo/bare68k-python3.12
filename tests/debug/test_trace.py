from __future__ import print_function

import pytest
import traceback

from bare68k import *
from bare68k.api import mem
from bare68k.consts import *
from bare68k.debug import *

RESET_OPCODE = 0x4e70
NOP_OPCODE = 0x4e71

MOVEM_TO_SP = 0x48e7fffe
MOVEM_FROM_SP = 0x4cdf7fff

def _setup_code(rt):
  PROG_BASE = rt.get_reset_pc()
  mem.w32(PROG_BASE, MOVEM_TO_SP)
  mem.w32(PROG_BASE+4, MOVEM_FROM_SP)
  mem.w16(PROG_BASE+8, RESET_OPCODE)
  mem.w16(PROG_BASE+10, RESET_OPCODE)

def test_trace_instr(rt):
  _setup_code(rt)
  # with trace
  trace.enable_instr_trace()
  rt.run()
  # without trace
  trace.disable_instr_trace()
  rt.run()

def test_trace_annotate_instr(rt):
  _setup_code(rt)
  # with trace
  def anno(pc, num_bytes):
    return "HUHU:%08x" % pc
  dump.set_instr_annotate_func(anno)
  trace.enable_instr_trace()
  rt.run()
  # without trace
  trace.disable_instr_trace()
  rt.run()
  dump.reset_instr_annotate_func()

def test_trace_annotate_exc(rt):
  _setup_code(rt)
  # with trace
  def anno(pc, num_bytes):
    raise ValueError("anno test fail!")
  dump.set_instr_annotate_func(anno)
  trace.enable_instr_trace()
  with pytest.raises(ValueError):
    rt.run()
  dump.reset_instr_annotate_func()

def test_trace_annotate_catch(rt):
  _setup_code(rt)
  # with trace
  def anno(pc, num_bytes):
    raise ValueError("anno test fail!")
  dump.set_instr_annotate_func(anno)
  trace.enable_instr_trace()
  try:
    rt.run()
  except ValueError as e:
    traceback.print_exc()
  dump.reset_instr_annotate_func()

def test_trace_cpu_mem(rt):
  _setup_code(rt)
  trace.enable_cpu_mem_trace()
  rt.run()

def test_trace_api_mem(rt):
  _setup_code(rt)
  trace.enable_api_mem_trace()
  rt.run()