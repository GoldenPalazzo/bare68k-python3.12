from bare68k.consts import *
from bare68k.errors import *

MEM_EMPTY= '_'
MEM_RAM = 'a'
MEM_ROM = 'o'
MEM_SPECIAL = 'S'
MEM_RESERVE = 'X'

PAGE_BYTES = 64 * 1024
PAGE_MASK  = 0xffff
PAGE_SHIFT = 16

class MemoryRange(object):
  def __init__(self, start_page, num_pages, mem_type, opts=None):
    self.start_page = start_page
    self.num_pages = num_pages
    self.mem_type = mem_type
    self.opts = opts
    self.next_page = self.start_page + self.num_pages

  def __repr__(self):
    return "MemoryRange(%d, %d, %s, %r)" % (self.start_page, self.num_pages,
      self.mem_type, self.opts)

  def __eq__(self, o):
    return self.start_page == o.start_page and self.num_pages == o.num_pages \
      and self.mem_type == o.mem_type and self.opts == o.opts


class MemoryConfig(object):
  """Configuration class for the memory layout of your m68k system"""

  def __init__(self, auto_align=False):
    """setup default memory config"""
    # auto align size requests that are not page aligned
    self.auto_align = auto_align
    # page list to see allocation
    self.range_list = []

  def _get_str_size(self, size_str, def_units):
    """get a size value from a string an honor K,M,G units

       returns (size_int, units_int)
    """
    n = len(size_str)
    if n < 1:
      raise ConfigError("Invalid size given: " + size_str)
    all_digits = size_str.isdigit()
    if all_digits:
      size = int(size_str)
      return (size, def_units)
    else:
      unit_str = size_str[-1].lower()
      if unit_str == 'k':
        units = 1024
      elif unit_str == 'm':
        units = 1024 * 1024
      elif unit_str == 'g':
        units = 1024 * 1024 * 1024
      elif unit_str == 'p': # for pages
        units = PAGE_BYTES
      else:
        raise ConfigError("Unknown size units: " + unit_str)
      size_str = size_str[:-1]
      if not size_str.isdigit():
        raise ConfigError("Invalid size given: " + size_str)
      size = int(size_str)
      return(size, units)

  def _get_num_pages(self, size, units):
    """get a size value and make sure its page aligned and return the pages"""
    if type(size) is str:
      n_size, n_units = self._get_str_size(size, units)
      total = n_size * n_units
    else:
      total = size * units
    print("TOTAL",total,self.auto_align)
    # is 64k page aligned?
    if total & PAGE_MASK != 0:
      if self.auto_align:
        pages = (total + PAGE_MASK) >> PAGE_SHIFT
      else:
        raise ConfigError("Size value %s (units %s) is not page aligned!" % (size, units))
    else:
      pages = total >> PAGE_SHIFT
    return pages

  def _get_page_addr(self, addr):
    """convert an absolute address to a page number"""
    return self._get_num_pages(addr, 1)

  def _store_page_range(self, begin_page, num_pages, mem_type, opts=None, sparse=False):
    """make sure the given page range fits in the page list"""
    # create a new range
    r = MemoryRange(begin_page, num_pages, mem_type, opts)
    # add to range_list
    rl = self.range_list
    if len(rl) == 0:
      # add first
      rl.append(r)
      return [r]
    else:
      # where to insert
      pos = 0
      res = []
      for e in rl:
        # lies before
        if r.start_page < e.start_page:
          # does fit
          if r.next_page <= e.start_page:
            rl.insert(pos, r)
            res.append(r)
            return res
          else:
            if sparse:
              # create partial range that fits
              np = e.start_page - r.start_page
              nr = MemoryRange(r.start_page, np, r.mem_type, r.opts)
              rl.insert(pos, nr)
              res.append(nr)
              # keep remainder
              r = MemoryRange(e.next_page, r.num_pages - np, r.mem_type, r.opts)
            else:
              raise ConfigError("%r overlaps %r!" % (r, e))
        # liese inside
        elif r.start_page < e.next_page:
          if not sparse:
            raise ConfigError("%r overlaps %r!" % (r, e))
        pos += 1
      # append to end
      rl.append(r)
      res.append(r)
      return res

  def _prepare_rom(self, data, pad):
    if data is None:
      return None
    n = len(data)
    rem = n % PAGE_BYTES
    if rem == 0:
      return data
    else:
      if pad is False:
        raise ConfigError("ROM needs padding")
      else:
        fill = PAGE_BYTES - rem
        if pad is True:
          pad = chr(0)
        else:
          pad = chr(pad)
        return data + pad * fill

  # page based

  def add_ram_range(self, begin_page, num_pages, sparse=False):
    return self._store_page_range(begin_page, num_pages, MEM_RAM, sparse=sparse)

  def add_rom_range(self, begin_page, num_pages, data=None, pad=False):
    rom = self._prepare_rom(data, pad)
    return self._store_page_range(begin_page, num_pages, MEM_ROM, opts=rom)

  def add_special_range(self, begin_page, num_pages, r_func, w_func):
    opts = (r_func, w_func)
    return self._store_page_range(begin_page, num_pages, MEM_SPECIAL, opts=opts)

  def add_reserve_range(self, begin_page, num_pages):
    return self._store_page_range(begin_page, num_pages, MEM_RESERVE)

  # address based

  def add_ram_range_addr(self, begin_addr, size, units=1024, sparse=False):
    begin_page = self._get_page_addr(begin_addr)
    num_pages = self._get_num_pages(size, units)
    return self.add_ram_range(begin_page, num_pages, sparse)

  def add_rom_range_addr(self, begin_addr, size, data=None, units=1024, pad=False):
    begin_page = self._get_page_addr(begin_addr)
    num_pages = self._get_num_pages(size, units)
    return self.add_rom_range(begin_page, num_pages, data, pad)

  def add_special_range_addr(self, begin_addr, size, r_func, w_func, units=1024):
    begin_page = self._get_page_addr(begin_addr)
    num_pages = self._get_num_pages(size, units)
    return self.add_special_range(begin_page, num_pages, r_func, w_func)

  def add_reserve_range_addr(self, begin_addr, size, units=1024):
    begin_page = self._get_page_addr(begin_addr)
    num_pages = self._get_num_pages(size, units)
    return self.add_reserve_range(begin_page, num_pages)

  # get result

  def get_range_list(self):
    """return the list of memory ranges currently allocated"""
    return self.range_list

  def get_page_list_str(self):
    """return a string showing page allocation"""
    s = ""
    rl = self.range_list
    if len(rl) == 0:
      return ""
    old_pos = 0
    for r in rl:
      pos = r.start_page
      space = pos - old_pos
      if space > 0:
        s += MEM_EMPTY * space
      np = r.num_pages
      s += r.mem_type * np
      old_pos = pos + r.num_pages
    return s

  def get_num_pages(self):
    """return the total number of pages required to handle the given layout"""
    rl = self.range_list
    if len(rl) == 0:
      return 0
    else:
      return rl[-1].next_page

  def check(self, ram_at_zero=True, max_pages=256):
    """check if gurrent layout is valid"""
    rl = self.range_list
    n = len(rl)
    if n == 0:
      raise ConfigError("no memory entries found!")
    elif n > max_pages:
      raise ConfigError("too many pages: want=%d max=%d" % (n, max_pages))
    if ram_at_zero:
      r = rl[0]
      if r.start_page > 0 or r.mem_type != MEM_RAM:
        raise ConfigError("no RAM at page 0!")
