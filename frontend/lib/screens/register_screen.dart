import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../theme/app_theme.dart';
import 'auth_web_shell.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  String _username = '';
  String _email = '';
  String _password = '';
  bool _loading = false;
  bool _obscurePassword = true;
  bool _obscurePasswordConfirmation = true;

  void _submit() async {
    if (!_formKey.currentState!.validate()) return;
    _formKey.currentState!.save();
    setState(() => _loading = true);
    final auth = Provider.of<AuthProvider>(context, listen: false);
    try {
      final res = await auth.register(_username, _email, _password);
      if (res['success'] == true) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Registered successfully. Please log in')));
        Navigator.of(context).pop();
      } else {
        final err = res['error'];
        if (!mounted) return;
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(err.toString())));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.mint,
      body: LayoutBuilder(builder: (context, constraints) {
        final isLarge = constraints.maxWidth >= 700;
        if (isLarge) {
          return AuthWebShell(
              child: _buildRegisterPanel(context, webMode: true));
        }

        return _MobileAuthScaffold(
          child: _buildRegisterPanel(context),
        );
      }),
    );
  }

  Widget _buildRegisterPanel(BuildContext context, {bool webMode = false}) {
    return Padding(
      padding: EdgeInsets.all(webMode ? 28 : 20),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const _AuthBrandMark(),
            SizedBox(height: webMode ? 24 : 18),
            Text(
              'Create your basket',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            Text(
              'Start comparing supermarket prices in seconds.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            SizedBox(height: webMode ? 26 : 20),
            _AuthFormPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextFormField(
                    decoration: const InputDecoration(
                      labelText: 'Name',
                      prefixIcon: Icon(Icons.person_outline_rounded),
                    ),
                    textInputAction: TextInputAction.next,
                    onSaved: (s) => _username = s ?? '',
                    validator: (s) =>
                        s == null || s.trim().isEmpty ? 'Required' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    decoration: const InputDecoration(
                      labelText: 'Email',
                      prefixIcon: Icon(Icons.mail_outline_rounded),
                    ),
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    onSaved: (s) => _email = s ?? '',
                    validator: (s) =>
                        s == null || s.trim().isEmpty ? 'Required' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    decoration: InputDecoration(
                      labelText: 'Password',
                      prefixIcon: const Icon(Icons.lock_outline_rounded),
                      suffixIcon: IconButton(
                        tooltip: _obscurePassword
                            ? 'Show password'
                            : 'Hide password',
                        icon: Icon(
                          _obscurePassword
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                          semanticLabel: _obscurePassword
                              ? 'Show password'
                              : 'Hide password',
                        ),
                        onPressed: () => setState(
                          () => _obscurePassword = !_obscurePassword,
                        ),
                      ),
                    ),
                    obscureText: _obscurePassword,
                    textInputAction: TextInputAction.next,
                    onChanged: (value) => _password = value,
                    onSaved: (s) => _password = s ?? '',
                    validator: (s) =>
                        s == null || s.length < 6 ? 'Use 6+ characters' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    decoration: InputDecoration(
                      labelText: 'Confirm password',
                      prefixIcon: const Icon(Icons.verified_user_outlined),
                      suffixIcon: IconButton(
                        tooltip: _obscurePasswordConfirmation
                            ? 'Show password confirmation'
                            : 'Hide password confirmation',
                        icon: Icon(
                          _obscurePasswordConfirmation
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                          semanticLabel: _obscurePasswordConfirmation
                              ? 'Show password confirmation'
                              : 'Hide password confirmation',
                        ),
                        onPressed: () => setState(
                          () => _obscurePasswordConfirmation =
                              !_obscurePasswordConfirmation,
                        ),
                      ),
                    ),
                    obscureText: _obscurePasswordConfirmation,
                    textInputAction: TextInputAction.done,
                    onFieldSubmitted: (_) => _loading ? null : _submit(),
                    validator: (s) {
                      if (s == null || s.isEmpty) return 'Required';
                      if (s != _password) return 'Passwords do not match';
                      return null;
                    },
                  ),
                  const SizedBox(height: 18),
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                        backgroundColor: AppColors.deepGreen,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      onPressed: _loading ? null : _submit,
                      child: _loading
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.4,
                                color: Colors.white,
                              ),
                            )
                          : const Text('Create account'),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text('Already have an account?',
                          style: Theme.of(context).textTheme.bodyMedium),
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Log in'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MobileAuthScaffold extends StatelessWidget {
  final Widget child;

  const _MobileAuthScaffold({required this.child});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(
          18,
          18,
          18,
          18 + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minHeight: MediaQuery.sizeOf(context).height -
                MediaQuery.paddingOf(context).vertical -
                36,
          ),
          child: Center(child: child),
        ),
      ),
    );
  }
}

class _AuthBrandMark extends StatelessWidget {
  const _AuthBrandMark();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        width: 104,
        height: 104,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(28),
          border: Border.all(color: Colors.white),
          boxShadow: [
            BoxShadow(
              color: AppColors.deepGreen.withOpacity(0.10),
              blurRadius: 24,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(22),
          child: Image.asset(
            'assets/app_images/applogo.jpeg',
            fit: BoxFit.contain,
          ),
        ),
      ),
    );
  }
}

class _AuthFormPanel extends StatelessWidget {
  final Widget child;

  const _AuthFormPanel({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white),
        boxShadow: [
          BoxShadow(
            color: AppColors.deepGreen.withOpacity(0.08),
            blurRadius: 28,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: child,
    );
  }
}
