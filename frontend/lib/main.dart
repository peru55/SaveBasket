import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/basket_provider.dart';
import 'providers/auth_provider.dart';
import 'providers/supermarket_provider.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'theme/app_theme.dart';

void main() {
  debugPrint('SaveBasket: main() starting');
  runApp(const SaveBasketApp());
}

class SaveBasketApp extends StatelessWidget {
  const SaveBasketApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
        providers: [
        ChangeNotifierProvider(create: (_) => BasketProvider()),
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => SupermarketProvider()),
      ],
      child: MaterialApp(
        title: 'SaveBasket',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        home: const _Root(),
      ),
    );
  }
}

class _Root extends StatefulWidget {
  const _Root();

  @override
  State<_Root> createState() => _RootState();
}

class _RootState extends State<_Root> with WidgetsBindingObserver {
  bool _initialized = false;
  bool? _wasLoggedIn;
  // cache auth provider to avoid using context in dispose
  dynamic _authProvider;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_initialized) {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      _authProvider = auth;
      debugPrint('SaveBasket: calling auth.init()');
      auth.init().then((_) {
        debugPrint(
            'SaveBasket: auth.init() completed, loggedIn=${auth.loggedIn}');
        setState(() {});
        _wasLoggedIn = auth.loggedIn;
      }).catchError((e, st) {
        debugPrint('SaveBasket: auth.init() error: $e');
        setState(() {});
      });
      // listen for auth state changes to show session-expired feedback
      auth.addListener(_authListener);
      _initialized = true;
    }
  }

  void _authListener() {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    // Only show feedback when we transition from logged in -> logged out
    if ((_wasLoggedIn ?? false) && !auth.loggedIn) {
      WidgetsBinding.instance.addPostFrameCallback((_) async {
        // show blocking dialog with retry option
        final choice = await showDialog<String>(
          context: context,
          barrierDismissible: false,
          builder: (ctx) {
            return AlertDialog(
              title: const Text('Session expired'),
              content: const Text(
                  'Your session has expired. Please log in again or retry refreshing your session.'),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop('retry'),
                  child: const Text('Retry'),
                ),
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop('login'),
                  child: const Text('Login'),
                ),
              ],
            );
          },
        );

        if (choice == 'retry') {
          final ok = await auth.refresh();
          if (!mounted) return;
          if (ok) {
            ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Session restored')));
          } else {
            // go to login
            await auth.logout();
            if (!mounted) return;
            Navigator.of(context).pushAndRemoveUntil(
                MaterialPageRoute(builder: (_) => const LoginScreen()),
                (r) => false);
          }
        } else {
          // user chose login
          await auth.logout();
          if (!mounted) return;
          Navigator.of(context).pushAndRemoveUntil(
              MaterialPageRoute(builder: (_) => const LoginScreen()),
              (r) => false);
        }
      });
    }
    _wasLoggedIn = auth.loggedIn;
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    // remove listener from cached provider instead of using context
    try {
      (_authProvider as AuthProvider).removeListener(_authListener);
    } catch (_) {}
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    if (state == AppLifecycleState.resumed) {
      // attempt silent refresh when app resumes
      auth.refresh();
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    if (!auth.loggedIn) {
      return const LoginScreen();
    }
    return const HomeScreen();
  }
}
