# encoding: UTF-8

import talib as ta
import numpy as np



from vnpy.trader.vtConstant import EMPTY_STRING, EMPTY_FLOAT
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate)
                                                     
                                                     


########################################################################
class A3Strategy(CtaTemplate):
    """基于Talib模块的双指数均线策略Demo"""

    className = 'A3Strategy'
    author = u'ideaplat'

    # 策略参数
    fastPeriod = 5      # 快速均线参数
    slowPeriod = 20     # 慢速均线参数
    initDays = 5        # 初始化数据所用的天数

    # 策略变量
    bar = None
    barMinute = EMPTY_STRING

    closeHistory = []       # 缓存K线收盘价的数组
    maxHistory = 50         # 最大缓存数量

    fastMa0 = EMPTY_FLOAT   # 当前最新的快速均线数值
    fastMa1 = EMPTY_FLOAT   # 上一根的快速均线数值

    slowMa0 = EMPTY_FLOAT   # 慢速均线数值
    slowMa1 = EMPTY_FLOAT


    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'fastPeriod',
                 'slowPeriod']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'fastMa0',
               'fastMa1',
               'slowMa0',
               'slowMa1']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(A3Strategy, self).__init__(ctaEngine, setting)

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双SMA演示策略初始化')

        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双SMA演示策略启动')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双SMA演示策略停止')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute

        if tickMinute != self.barMinute:
            if self.bar:
                self.onBar(self.bar)

            bar = CtaBarData()
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange

            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime  # K线的时间设为第一个Tick的时间

            # 实盘中用不到的数据可以选择不算，从而加快速度
            # bar.volume = tick.volume
            # bar.openInterest = tick.openInterest

            self.bar = bar  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute  # 更新当前的分钟

        else:  # 否则继续累加新的K线
            bar = self.bar  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 把最新的收盘价缓存到列表中
        self.closeHistory.append(bar.close)

        # 检查列表长度，如果超过缓存上限则移除最老的数据
        # 这样是为了减少计算用的数据量，提高速度
        if len(self.closeHistory) > self.maxHistory:
            self.closeHistory.pop(0)
        # 如果小于缓存上限，则说明初始化数据尚未足够，不进行后续计算
        else:
            return

        # 将缓存的收盘价数转化为numpy数组后，传入talib的函数SMA中计算
        closeArray = np.array(self.closeHistory)
        fastSMA = ta.SMA(closeArray, self.fastPeriod)
        slowSMA = ta.SMA(closeArray, self.slowPeriod)

        # 读取当前K线和上一根K线的数值，用于判断均线交叉
        self.fastMa0 = fastSMA[-1]
        self.fastMa1 = fastSMA[-2]
        self.slowMa0 = slowSMA[-1]
        self.slowMa1 = slowSMA[-2]

        # 判断买卖
        crossOver = self.fastMa0>self.slowMa0 and self.fastMa1<self.slowMa1     # 金叉上穿
        crossBelow = self.fastMa0<self.slowMa0 and self.fastMa1>self.slowMa1    # 死叉下穿

        # 金叉和死叉的条件是互斥
        if crossOver:
            # 如果金叉时手头没有持仓，则直接做多
            if self.pos == 0:
                self.buy(bar.close, 1)
            # 如果有空头持仓，则先平空，再做多
            elif self.pos < 0:
                self.cover(bar.close, 1)
                self.buy(bar.close, 1)
        # 死叉和金叉相反
        elif crossBelow:
            if self.pos == 0:
                self.short(bar.close, 1)
            elif self.pos > 0:
                self.sell(bar.close, 1)
                self.short(bar.close, 1)

        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
def runBacktesting():
    from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, MINUTE_DB_NAME
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    bd = {'start':'20110801','capital':10000,'slippage':1,'rate':1.0/10000,'size':10,'priceTick':1,'symbol':'rb0000','stratName':'A3Strategy'}
    #bd = {'start':'20150327','capital':200000,'slippage':1,'rate':1.0/10000,'size':1,'priceTick':1,'symbol':'ni0000','stratName':'A3Strategy'}
    #bd = {'start':'20140228','capital':200000,'slippage':1,'rate':1.0/10000,'size':5,'priceTick':1,'symbol':'pp0000','stratName':'A3Strategy'}
    #bd = {'start':'20080624','capital':200000,'slippage':1,'rate':1.0/10000,'size':5,'priceTick':5,'symbol':'l0000','stratName':'A3Strategy'}
    # 设置回测用的数据起始日期
    engine.setStartDate(bd['start'])
    
    # 设置产品相关参数
    engine.setCapital(bd['capital'])
    engine.setSlippage(bd['slippage'])     # 滑点 
    engine.setRate(bd['rate'])   # 手续费 
    engine.setSize(bd['size'])         # 合约大小 
    engine.setPriceTick(bd['priceTick'])    # 最小价格变动
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, bd['symbol'])
    engine.stratName = bd['stratName']
    engine.symbol = bd['symbol']
    
    # 在引擎中创建策略对象
    d = {}
    engine.initStrategy(A3Strategy, d)
    
    # 开始跑回测
    engine.runBacktesting()
    
    # 显示回测结果
    #engine.showBacktestingResult()
    #engine.showDailyResult()
    engine.saveDailyResult()
    
def runOptimization():
    from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, MINUTE_DB_NAME, OptimizationSetting
    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)
    
    bd = {'start':'20110801','capital':10000,'slippage':1,'rate':1.0/10000,'size':10,'priceTick':1,'symbol':'rb0000','stratName':'A3Strategy'}
    # 设置回测用的数据起始日期
    engine.setStartDate(bd['start'])
    
    # 设置产品相关参数
    engine.setCapital(bd['capital'])
    engine.setSlippage(bd['slippage'])     # 股指1跳
    engine.setRate(bd['rate'])   # 万0.3
    engine.setSize(bd['size'])         # 股指合约大小 
    engine.setPriceTick(bd['priceTick'])    # 股指最小价格变动
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, bd['symbol'])
    engine.stratName = bd['stratName']
    engine.symbolName = bd['symbol']
    
    # 跑优化
    setting = OptimizationSetting()                 # 新建一个优化任务设置对象
    setting.setOptimizeTarget('totalNetPnl')            # 设置优化排序的目标是策略净盈利 sharpeRatio totalNetPnl endBalance
    
    #setting.addParameter('stop_loss', 10, 100, 5)    # 增加第一个优化参数atrLength，起始12，结束20，步进2
    setting.addParameter('fastPeriod', 5, 30, 5)  
    setting.addParameter('slowPeriod', 60)  
    

    # 性能测试环境：I7-3770，主频3.4G, 8核心，内存16G，Windows 7 专业版
    # 测试时还跑着一堆其他的程序，性能仅供参考
    import time    
    start = time.time()
    
    # 运行单进程优化函数，自动输出结果，耗时：359秒
    #engine.runOptimization(BollingerStrategy, setting)            
    
    # 多进程优化，耗时：89秒
    #engine.runParallelOptimization(BollingerStrategy, setting)
    engine.saveParallelOptimization(A3Strategy, setting)
         
        
    print u'耗时：%s' %(time.time()-start)   
    
if __name__ == '__main__':
    runBacktesting()
    #runOptimization()