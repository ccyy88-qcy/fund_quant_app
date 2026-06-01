import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fund_quant_app/main.dart';

void main() {
  testWidgets('App launches with dashboard', (WidgetTester tester) async {
    await tester.pumpWidget(const FundQuantApp());
    expect(find.text('基金量化工具'), findsWidgets);
  });
}
