import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/main.dart';

void main() {
  testWidgets('Smoke test: Renders SaveBasketApp without crashing', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const SaveBasketApp());

    // Verify that the title 'SaveBasket Kenya' is rendered.
    expect(find.text('SaveBasket Kenya'), findsOneWidget);
  });
}
