import 'package:dio/dio.dart';
import 'dart:convert';

/// 申万二级行业月度涨跌幅数据服务
/// 直接调用东方财富 HTTP 接口，无需后端
class SectorDataService {
  static final SectorDataService _instance = SectorDataService._internal();
  factory SectorDataService() => _instance;
  SectorDataService._internal();

  final Dio _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 30),
    headers: {
      'User-Agent': 'Mozilla/5.0 (Linux; Android 16; Pixel 9) AppleWebKit/537.36',
      'Referer': 'https://quote.eastmoney.com/',
    },
  ));

  /// 131个申万二级行业代码+名称+上级行业
  static const List<Map<String, String>> sectors = [
    {'code': '801016', 'name': '种植业', 'parent': '农林牧渔'},
    {'code': '801015', 'name': '渔业', 'parent': '农林牧渔'},
    {'code': '801011', 'name': '林业Ⅱ', 'parent': '农林牧牧渔'},
    {'code': '801014', 'name': '饲料', 'parent': '农林牧渔'},
    {'code': '801012', 'name': '农产品加工', 'parent': '农林牧渔'},
    {'code': '801017', 'name': '养殖业', 'parent': '农林牧渔'},
    {'code': '801018', 'name': '动物保健Ⅱ', 'parent': '农林牧渔'},
    {'code': '801019', 'name': '农业综合Ⅱ', 'parent': '农林牧渔'},
    {'code': '801033', 'name': '化学原料', 'parent': '基础化工'},
    {'code': '801034', 'name': '化学制品', 'parent': '基础化工'},
    {'code': '801035', 'name': '化学纤维', 'parent': '基础化工'},
    {'code': '801036', 'name': '塑料', 'parent': '基础化工'},
    {'code': '801037', 'name': '橡胶', 'parent': '基础化工'},
    {'code': '801038', 'name': '农化制品', 'parent': '基础化工'},
    {'code': '801051', 'name': '非金属材料Ⅱ', 'parent': '基础化工'},
    {'code': '801052', 'name': '冶钢原料', 'parent': '钢铁'},
    {'code': '801053', 'name': '普钢', 'parent': '钢铁'},
    {'code': '801054', 'name': '特钢Ⅱ', 'parent': '钢铁'},
    {'code': '801055', 'name': '金属新材料', 'parent': '有色金属'},
    {'code': '801056', 'name': '贵金属', 'parent': '有色金属'},
    {'code': '801057', 'name': '小金属', 'parent': '有色金属'},
    {'code': '801058', 'name': '能源金属', 'parent': '有色金属'},
    {'code': '801070', 'name': '半导体', 'parent': '电子'},
    {'code': '801081', 'name': '半导体', 'parent': '电子'},
    {'code': '801082', 'name': '元件', 'parent': '电子'},
    {'code': '801083', 'name': '元件', 'parent': '电子'},
    {'code': '801084', 'name': '光学光电子', 'parent': '电子'},
    {'code': '801085', 'name': '消费电子', 'parent': '电子'},
    {'code': '801086', 'name': '电子化学品Ⅱ', 'parent': '电子'},
    {'code': '801090', 'name': '其他电子Ⅱ', 'parent': '电子'},
    {'code': '801101', 'name': '汽车零部件', 'parent': '汽车'},
    {'code': '801102', 'name': '汽车服务', 'parent': '汽车'},
    {'code': '801103', 'name': '摩托车及其他', 'parent': '汽车'},
    {'code': '801104', 'name': '乘用车', 'parent': '汽车'},
    {'code': '801105', 'name': '商用车', 'parent': '汽车'},
    {'code': '801111', 'name': '白色家电', 'parent': '家用电器'},
    {'code': '801112', 'name': '黑色家电', 'parent': '家用电器'},
    {'code': '801113', 'name': '小家电', 'parent': '家用电器'},
    {'code': '801114', 'name': '厨卫电器', 'parent': '家用电器'},
    {'code': '801115', 'name': '照明设备Ⅱ', 'parent': '家用电器'},
    {'code': '801116', 'name': '家电零部件', 'parent': '家用电器'},
    {'code': '801117', 'name': '其他家电Ⅱ', 'parent': '家用电器'},
    {'code': '801121', 'name': '食品加工', 'parent': '食品饮料'},
    {'code': '801122', 'name': '白酒Ⅱ', 'parent': '食品饮料'},
    {'code': '801123', 'name': '非白酒', 'parent': '食品饮料'},
    {'code': '801124', 'name': '饮料乳品', 'parent': '食品饮料'},
    {'code': '801125', 'name': '休闲食品', 'parent': '食品饮料'},
    {'code': '801126', 'name': '调味发酵品Ⅱ', 'parent': '食品饮料'},
    {'code': '801131', 'name': '纺织制造', 'parent': '纺织服饰'},
    {'code': '801132', 'name': '服装家纺', 'parent': '纺织服饰'},
    {'code': '801133', 'name': '饰品', 'parent': '纺织服饰'},
    {'code': '801141', 'name': '造纸', 'parent': '轻工制造'},
    {'code': '801142', 'name': '包装印刷', 'parent': '轻工制造'},
    {'code': '801143', 'name': '家居用品', 'parent': '轻工制造'},
    {'code': '801144', 'name': '文娱用品', 'parent': '轻工制造'},
    {'code': '801151', 'name': '化学制药', 'parent': '医药生物'},
    {'code': '801152', 'name': '中药Ⅱ', 'parent': '医药生物'},
    {'code': '801153', 'name': '生物制品', 'parent': '医药生物'},
    {'code': '801154', 'name': '医药商业', 'parent': '医药生物'},
    {'code': '801155', 'name': '医疗器械', 'parent': '医药生物'},
    {'code': '801156', 'name': '医疗服务', 'parent': '医药生物'},
    {'code': '801161', 'name': '电力', 'parent': '公用事业'},
    {'code': '801162', 'name': '燃气Ⅱ', 'parent': '公用事业'},
    {'code': '801163', 'name': '物流', 'parent': '交通运输'},
    {'code': '801164', 'name': '铁路公路', 'parent': '交通运输'},
    {'code': '801165', 'name': '航空机场', 'parent': '交通运输'},
    {'code': '801166', 'name': '航运港口', 'parent': '交通运输'},
    {'code': '801171', 'name': '房地产开发', 'parent': '房地产'},
    {'code': '801172', 'name': '房地产服务', 'parent': '房地产'},
    {'code': '801181', 'name': '贸易Ⅱ', 'parent': '商贸零售'},
    {'code': '801182', 'name': '一般零售', 'parent': '商贸零售'},
    {'code': '801183', 'name': '专业连锁Ⅱ', 'parent': '商贸零售'},
    {'code': '801184', 'name': '互联网电商', 'parent': '商贸零售'},
    {'code': '801191', 'name': '旅游零售Ⅱ', 'parent': '社会服务'},
    {'code': '801192', 'name': '专业服务', 'parent': '社会服务'},
    {'code': '801193', 'name': '酒店餐饮', 'parent': '社会服务'},
    {'code': '801194', 'name': '旅游及景区', 'parent': '社会服务'},
    {'code': '801195', 'name': '教育', 'parent': '社会服务'},
    {'code': '801201', 'name': '国有大型银行Ⅱ', 'parent': '银行'},
    {'code': '801202', 'name': '股份制银行', 'parent': '银行'},
    {'code': '801203', 'name': '城商行Ⅱ', 'parent': '银行'},
    {'code': '801204', 'name': '农商行Ⅱ', 'parent': '银行'},
    {'code': '801211', 'name': '证券Ⅱ', 'parent': '非银金融'},
    {'code': '801212', 'name': '保险Ⅱ', 'parent': '非银金融'},
    {'code': '801213', 'name': '多元金融', 'parent': '非银金融'},
    {'code': '801221', 'name': '综合Ⅱ', 'parent': '非银金融'},
    {'code': '801711', 'name': '水泥', 'parent': '建筑材料'},
    {'code': '801712', 'name': '玻璃玻纤', 'parent': '建筑材料'},
    {'code': '801713', 'name': '装修建材', 'parent': '建筑材料'},
    {'code': '801714', 'name': '房屋建设Ⅱ', 'parent': '建筑材料'},
    {'code': '801715', 'name': '装修装饰Ⅱ', 'parent': '建筑材料'},
    {'code': '801721', 'name': '基础建设', 'parent': '建筑装饰'},
    {'code': '801722', 'name': '专业工程', 'parent': '建筑装饰'},
    {'code': '801723', 'name': '工程咨询服务Ⅱ', 'parent': '建筑装饰'},
    {'code': '801731', 'name': '电机Ⅱ', 'parent': '电力设备'},
    {'code': '801732', 'name': '其他电源设备Ⅱ', 'parent': '电力设备'},
    {'code': '801733', 'name': '光伏设备', 'parent': '电力设备'},
    {'code': '801734', 'name': '风电设备', 'parent': '电力设备'},
    {'code': '801735', 'name': '电池', 'parent': '电力设备'},
    {'code': '801736', 'name': '电网设备', 'parent': '电力设备'},
    {'code': '801741', 'name': '通用设备', 'parent': '机械设备'},
    {'code': '801742', 'name': '专用设备', 'parent': '机械设备'},
    {'code': '801743', 'name': '轨交设备Ⅱ', 'parent': '机械设备'},
    {'code': '801744', 'name': '工程机械', 'parent': '机械设备'},
    {'code': '801745', 'name': '自动化设备', 'parent': '机械设备'},
    {'code': '801751', 'name': '航天装备Ⅱ', 'parent': '国防军工'},
    {'code': '801752', 'name': '航空装备Ⅱ', 'parent': '国防军工'},
    {'code': '801753', 'name': '地面兵装Ⅱ', 'parent': '国防军工'},
    {'code': '801754', 'name': '航海装备Ⅱ', 'parent': '国防军工'},
    {'code': '801755', 'name': '军工电子Ⅱ', 'parent': '国防军工'},
    {'code': '801761', 'name': '计算机设备', 'parent': '计算机'},
    {'code': '801762', 'name': 'IT服务Ⅱ', 'parent': '计算机'},
    {'code': '801763', 'name': '软件开发', 'parent': '计算机'},
    {'code': '801764', 'name': '游戏Ⅱ', 'parent': '传媒'},
    {'code': '801765', 'name': '广告营销', 'parent': '传媒'},
    {'code': '801766', 'name': '影视院线', 'parent': '传媒'},
    {'code': '801767', 'name': '数字媒体', 'parent': '传媒'},
    {'code': '801768', 'name': '出版', 'parent': '传媒'},
    {'code': '801769', 'name': '电视广播', 'parent': '传媒'},
    {'code': '801771', 'name': '通信设备', 'parent': '通信'},
    {'code': '801772', 'name': '煤炭开采', 'parent': '煤炭'},
    {'code': '801773', 'name': '焦炭Ⅱ', 'parent': '煤炭'},
    {'code': '801774', 'name': '油气开采Ⅱ', 'parent': '石油石化'},
    {'code': '801775', 'name': '油服工程', 'parent': '石油石化'},
    {'code': '801776', 'name': '炼化及贸易', 'parent': '石油石化'},
    {'code': '801781', 'name': '环境治理', 'parent': '环保'},
    {'code': '801782', 'name': '环保设备Ⅱ', 'parent': '环保'},
    {'code': '801911', 'name': '个护用品', 'parent': '美容护理'},
    {'code': '801912', 'name': '化妆品', 'parent': '美容护理'},
    {'code': '801913', 'name': '医疗美容', 'parent': '美容护理'},
    {'code': '801921', 'name': '电力', 'parent': '公用事业'},
    {'code': '801931', 'name': '燃气Ⅱ', 'parent': '公用事业'},
    {'code': '801941', 'name': '物流', 'parent': '交通运输'},
    {'code': '801951', 'name': '铁路公路', 'parent': '交通运输'},
    {'code': '801961', 'name': '油气开采Ⅱ', 'parent': '石油石化'},
    {'code': '801971', 'name': '航空机场', 'parent': '交通运输'},
    {'code': '801981', 'name': '航运港口', 'parent': '交通运输'},
    {'code': '801982', 'name': '炼化及贸易', 'parent': '石油石化'},
    {'code': '801983', 'name': '医疗美容', 'parent': '美容护理'},
    {'code': '801991', 'name': '环境治理', 'parent': '环保'},
  ];

  /// 获取单个行业月度K线数据
  Future<Map<String, dynamic>?> fetchSectorKline(String code, {int days = 60}) async {
    try {
      final now = DateTime.now();
      final endDate = '${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}';
      final startDate = '${now.year - 1}0101';

      final url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get';
      final params = {
        'secid': '90.$code',
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': '101',  // 日K
        'fqt': '0',
        'end': endDate,
        'lmt': days.toString(),
      };

      final resp = await _dio.get(url, queryParameters: params);
      final data = resp.data;

      if (data == null || data['data'] == null || data['data']['klines'] == null) {
        return null;
      }

      final klines = data['data']['klines'] as List;
      if (klines.isEmpty) return null;

      // 解析K线数据
      // f51=日期, f52=开盘, f53=收盘, f54=最高, f55=最低, f56=成交量, f57=成交额, f58=振幅, f59=涨跌幅, f60=涨跌额, f61=换手率
      List<Map<String, dynamic>> parsed = [];
      for (var k in klines) {
        final parts = (k as String).split(',');
        if (parts.length >= 11) {
          parsed.add({
            'date': parts[0],
            'open': double.tryParse(parts[1]) ?? 0,
            'close': double.tryParse(parts[2]) ?? 0,
            'high': double.tryParse(parts[3]) ?? 0,
            'low': double.tryParse(parts[4]) ?? 0,
            'volume': double.tryParse(parts[5]) ?? 0,
            'amount': double.tryParse(parts[6]) ?? 0,
            'amplitude': double.tryParse(parts[7]) ?? 0,
            'change_pct': double.tryParse(parts[8]) ?? 0,
            'change': double.tryParse(parts[9]) ?? 0,
            'turnover': double.tryParse(parts[10]) ?? 0,
          });
        }
      }

      if (parsed.isEmpty) return null;

      // 计算月度指标
      final monthStart = parsed.first;
      final monthEnd = parsed.last;
      final startPrice = monthStart['open']!;
      final endPrice = monthEnd['close']!;
      final monthChg = startPrice > 0 ? ((endPrice / startPrice) - 1) * 100 : 0;

      // 涨跌天数
      int upDays = 0, downDays = 0, flatDays = 0;
      double totalChg = 0;
      double maxDaily = -999, minDaily = 999;

      for (var k in parsed) {
        final chg = k['change_pct'] as double;
        totalChg += chg;
        if (chg > maxDaily) maxDaily = chg;
        if (chg < minDaily) minDaily = chg;
        if (k['close']! > k['open']!) {
          upDays++;
        } else if (k['close']! < k['open']!) {
          downDays++;
        } else {
          flatDays++;
        }
      }

      // 60日最高价
      double h60High = 0;
      for (var k in parsed) {
        if (k['high']! > h60High) h60High = k['high']!;
      }
      final maxDrawdown = h60High > 0 ? ((endPrice / h60High) - 1) * 100 : 0;

      // 平均日涨跌幅
      final avgDailyChg = parsed.isNotEmpty ? totalChg / parsed.length : 0;

      // 最新价（实时）
      final realtimePrice = await _fetchRealtimePrice(code);

      return {
        'code': code,
        'start_price': startPrice,
        'end_price': realtimePrice ?? endPrice,
        'kline_end': endPrice,
        'month_chg_pct': double.parse(monthChg.toStringAsFixed(2)),
        'max_drawdown_60d': double.parse(maxDrawdown.toStringAsFixed(2)),
        'up_days': upDays,
        'down_days': downDays,
        'flat_days': flatDays,
        'trading_days': parsed.length,
        'avg_daily_chg': double.parse(avgDailyChg.toStringAsFixed(2)),
        'max_daily_chg': double.parse(maxDaily.toStringAsFixed(2)),
        'min_daily_chg': double.parse(minDaily.toStringAsFixed(2)),
        'h60_high': h60High,
        'latest_date': parsed.last['date'],
        'kline_data': parsed,
      };
    } catch (e) {
      return null;
    }
  }

  /// 获取实时价格
  Future<double?> _fetchRealtimePrice(String code) async {
    try {
      final url = 'https://push2.eastmoney.com/api/qt/stock/get';
      final params = {
        'secid': '90.$code',
        'fields': 'f43,f44,f45,f46,f47,f48,f169,f170',
      };
      final resp = await _dio.get(url, queryParameters: params);
      final data = resp.data?['data'];
      if (data != null) {
        return (data['f43'] as num?)?.toDouble();
      }
    } catch (_) {}
    return null;
  }

  /// 批量获取所有行业月度涨跌幅（带并发控制）
  Future<List<Map<String, dynamic>>> fetchAllSectorsMonthly() async {
    List<Map<String, dynamic>> results = [];
    List<Future<Map<String, dynamic>?>> futures = [];

    // 每批5个并发，避免被限流
    for (int i = 0; i < sectors.length; i += 5) {
      final batch = sectors.sublist(i, (i + 5).clamp(0, sectors.length));
      futures = [];
      for (var s in batch) {
        futures.add(fetchSectorKline(s['code']!));
      }
      final batchResults = await Future.wait(futures);
      for (var r in batchResults) {
        if (r != null) {
          // 补充名称和上级行业
          final sector = sectors.firstWhere(
            (s) => s['code'] == r['code'],
            orElse: () => {'name': '', 'parent': ''},
          );
          r['name'] = sector['name'];
          r['parent'] = sector['parent'];
          results.add(r);
        }
      }
      // 短暂延迟避免限流
      await Future.delayed(const Duration(milliseconds: 200));
    }

    // 按涨跌幅排序
    results.sort((a, b) => (b['month_chg_pct'] as double).compareTo(a['month_chg_pct'] as double));
    return results;
  }
}
