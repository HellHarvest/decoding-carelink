
from decocare import commands, history, cgm
from decocare import lib
import types

class Task (object):
  def __init__ (self, msg, handler=None, **kwargs):
    self.msg = msg
    if handler:
      self.func = handler
  def __get__ (self, obj, objtype=None):
    if obj is None:
      return self
    else:
      return types.MethodType(self, obj)
  @staticmethod
  def func (self, response):
    return response.getData( )
  def __call__ (self, inst, **kwds):
    # print "__calll__", inst, self.func
    # self.func( )
    self.response = inst.session.query(self.msg, **kwds)
    return types.MethodType(self.func, inst)(self.response)
    # return self.response.getData( )

  @classmethod
  def handler (klass, msg, **kwargs):
    def closure (func):
      return Task(msg, handler=func, **kwargs)
    return closure

class Cursor (object):
  # Info
  # Page
  def __init__ (self, inst, **kwds):
    self.inst = inst
    self.kwds = kwds
  def get_page_info (self):
    self.info = self.inst.session.query(self.Info)
  def download_page (self, num):
    page = self.inst.session.query(self.Page, page=num)
    for record in self.find_records(page):
      yield record
  def range (self, info):
    raise NotImplemented( )
  def find_records (self, response):
    raise NotImplemented( )
  def iter (self):
    self.get_page_info( )
    for n in self.range(self.info.getData( )):
      yield self.download_page(n)

class PageIterator (Task):

  def __init__ (self, Cursor=None, handler=None):
    self.Cursor = Cursor
    if handler:
      self.func = handler

  def __call__ (self, inst, **kwds):
    self.pager = self.Cursor(inst, **kwds)
    for page in self.pager.iter( ):
      for record in page:
        yield record

  @classmethod
  def handler (klass, **kwargs):
    def closure (func):
      return klass(func, **kwargs)
    return closure


class PumpModel (object):
  bolus_strokes = 20
  basal_strokes = 40
  larger = False
  def __init__(self, model, session):
    self.model = model
    self.session = session

  read_status = Task(commands.ReadPumpStatus)
  read_temp_basal = Task(commands.ReadBasalTemp)
  read_settings = Task(commands.ReadSettings)
  read_reservoir = Task(commands.ReadRemainingInsulin)
  read_carb_ratios = Task(commands.ReadCarbRatios)
  read_current_glucose_pages = Task(commands.ReadCurGlucosePageNumber)
  read_current_history_pages = Task(commands.ReadCurPageNumber)

  @PageIterator.handler( )
  class iter_glucose_pages (Cursor):
    Info = commands.ReadCurGlucosePageNumber
    Page = commands.ReadGlucoseHistory
    def range (self, info):
      start = int(info['page'])
      end = start - int(info['glucose'])
      return xrange(start, end, -1)
    def find_records (self, response):
      page = cgm.PagedData.Data(response.data, larger=self.inst.larger)
      return page.decode( )

  @PageIterator.handler( )
  class iter_history_pages (Cursor):
    Info = commands.ReadCurPageNumber
    Page = commands.ReadHistoryData
    def range (self, info):
      start = 0
      end = int(info)
      return xrange(start, end)
    def find_records (self, response):
      decoder = history.HistoryPage(response.data, self.inst)
      records = decoder.decode( )
      return records

  @Task.handler(commands.ReadHistoryData)
  def read_history_data (self, response):
    decoder = history.HistoryPage(response.data, self)
    records = decoder.decode( )
    return records

  @Task.handler(commands.ReadGlucoseHistory)
  def read_glucose_data (self, response):
    records = [ ]
    page = cgm.PagedData.Data(response.data, larger=self.larger)
    records.extend(page.decode( ))
    return records

  @Task.handler(commands.ReadSettings)
  def my_read_settings (self, response):
    self.settings = response.getData( )
    return self.settings

  @Task.handler(commands.ReadRTC)
  def read_clock (self, response):
    clock = lib.parse.date(response.getData( ))
    return clock


class Model508 (PumpModel):
  pass

class Model511 (Model508):
  pass

class Model512 (Model511):
  pass

class Model515 (Model512):
  pass

class Model522 (Model515):
  pass

class Model523 (Model522):
  larger = True
  pass

class Model530 (Model523):
  pass

class Model540 (Model530):
  pass

class Model554 (Model540):
  pass

known = {
  '508': Model508
, '511': Model511
, '512': Model512
, '515': Model515
, '522': Model522
, '523': Model523
, '530': Model530
, '540': Model540
, '554': Model554
}

def lookup (model, session):
  klass = known.get(model, PumpModel)
  return klass(model, session)

