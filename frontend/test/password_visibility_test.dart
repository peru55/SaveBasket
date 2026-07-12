import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/screens/login_screen.dart';
import 'package:frontend/screens/register_screen.dart';

EditableText editableField(WidgetTester tester, int fieldIndex) {
  return tester.widget<EditableText>(
    find.descendant(
      of: find.byType(TextFormField).at(fieldIndex),
      matching: find.byType(EditableText),
    ),
  );
}

void useDesktopTestViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(650, 1000);
  tester.view.devicePixelRatio = 1;
  tester.platformDispatcher.textScaleFactorTestValue = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
}

void main() {
  testWidgets('login password can be shown and hidden', (tester) async {
    useDesktopTestViewport(tester);
    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));

    EditableText passwordField = editableField(tester, 1);
    expect(passwordField.obscureText, isTrue);

    await tester.tap(find.byTooltip('Show password'));
    await tester.pump();

    passwordField = editableField(tester, 1);
    expect(passwordField.obscureText, isFalse);
    expect(find.byTooltip('Hide password'), findsOneWidget);
  });

  testWidgets('registration password toggles are independent', (tester) async {
    useDesktopTestViewport(tester);
    await tester.pumpWidget(const MaterialApp(home: RegisterScreen()));

    expect(editableField(tester, 2).obscureText, isTrue);
    expect(editableField(tester, 3).obscureText, isTrue);

    await tester.tap(find.byTooltip('Show password'));
    await tester.pump();

    expect(editableField(tester, 2).obscureText, isFalse);
    expect(editableField(tester, 3).obscureText, isTrue);

    await tester.tap(find.byTooltip('Show password confirmation'));
    await tester.pump();

    expect(editableField(tester, 2).obscureText, isFalse);
    expect(editableField(tester, 3).obscureText, isFalse);
  });
}
