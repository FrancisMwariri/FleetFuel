import 'package:flutter/material.dart';

import '../app_theme.dart';
import '../data/api_client.dart';
import '../data/app_controller.dart';

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _obscure = true;
  bool _remember = true;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (_email.text.trim().isEmpty || _password.text.isEmpty) {
      _show('Enter your email and password.');
      return;
    }
    try {
      await widget.controller.login(_email.text, _password.text, remember: _remember);
    } on ApiException catch (error) {
      _show(error.message);
    } catch (_) {
      _show('Could not reach MediFuel. Check the API address and connection.');
    }
  }

  void _show(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _forgotPassword() async {
    final email = _email.text.trim();
    if (email.isEmpty) {
      _show('Enter your email first.');
      return;
    }
    try {
      await widget.controller.requestPasswordReset(email);
      _show('If the account exists, reset instructions will be sent.');
    } on ApiException catch (error) {
      _show(error.message);
    } catch (_) {
      _show('Could not reach the server. Try again when online.');
    }
  }

  Future<void> _openInviteRegistration() async {
    final token = await showDialog<String>(
      context: context,
      builder: (context) => const _InvitationTokenDialog(),
    );
    if (token == null || token.isEmpty || !mounted) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => InvitationRegistrationScreen(
        controller: widget.controller,
        invitationToken: token,
        onCreated: (email) {
          _email.text = email;
          _show('Account created. Sign in to your fleet.');
        },
      ),
    ));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.white,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: ListView(
                padding: const EdgeInsets.fromLTRB(28, 56, 28, 28),
                children: [
                  const _BrandLockup(centered: true),
                  const SizedBox(height: 44),
                  Text('Sign in to your account', style: Theme.of(context).textTheme.headlineMedium),
                  const SizedBox(height: 24),
                  Text('Email', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _email,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    autofillHints: const [AutofillHints.username, AutofillHints.email],
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.person_outline),
                      hintText: 'name@medifuel.ke',
                    ),
                  ),
                  const SizedBox(height: 20),
                  Text('Password', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _password,
                    obscureText: _obscure,
                    textInputAction: TextInputAction.done,
                    autofillHints: const [AutofillHints.password],
                    onSubmitted: (_) => _login(),
                    decoration: InputDecoration(
                      prefixIcon: const Icon(Icons.lock_outline),
                      hintText: 'Enter your password',
                      suffixIcon: IconButton(
                        tooltip: _obscure ? 'Show password' : 'Hide password',
                        onPressed: () => setState(() => _obscure = !_obscure),
                        icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                      ),
                    ),
                  ),
                  Wrap(
                    alignment: WrapAlignment.spaceBetween,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Checkbox(value: _remember, onChanged: (value) => setState(() => _remember = value ?? true)),
                          const Text('Remember me'),
                        ],
                      ),
                      TextButton(onPressed: _forgotPassword, child: const Text('Forgot password?')),
                    ],
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: widget.controller.busy ? null : _login,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      child: widget.controller.busy
                          ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('Log in'),
                    ),
                  ),
                  const SizedBox(height: 18),
                  const Row(children: [Expanded(child: Divider()), Padding(padding: EdgeInsets.symmetric(horizontal: 12), child: Text('or')), Expanded(child: Divider())]),
                  const SizedBox(height: 18),
                  OutlinedButton.icon(
                    onPressed: null,
                    icon: const Icon(Icons.g_mobiledata, size: 30),
                    label: const Text('Continue with Google'),
                  ),
                  const SizedBox(height: 42),
                  Center(
                    child: Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        const Text("Don't have an account? "),
                        TextButton(onPressed: _openInviteRegistration, child: const Text('Sign up')),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}

class _InvitationTokenDialog extends StatefulWidget {
  const _InvitationTokenDialog();

  @override
  State<_InvitationTokenDialog> createState() => _InvitationTokenDialogState();
}

class _InvitationTokenDialogState extends State<_InvitationTokenDialog> {
  final _token = TextEditingController();

  @override
  void dispose() {
    _token.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Invitation required'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Ask your fleet administrator for a one-time invitation token.'),
            const SizedBox(height: 16),
            TextField(controller: _token, decoration: const InputDecoration(labelText: 'Invitation token')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, _token.text.trim()), child: const Text('Continue')),
        ],
      );
}

class InvitationRegistrationScreen extends StatefulWidget {
  const InvitationRegistrationScreen({
    super.key,
    required this.controller,
    required this.invitationToken,
    required this.onCreated,
  });

  final AppController controller;
  final String invitationToken;
  final ValueChanged<String> onCreated;

  @override
  State<InvitationRegistrationScreen> createState() => _InvitationRegistrationScreenState();
}

class _InvitationRegistrationScreenState extends State<InvitationRegistrationScreen> {
  final _name = TextEditingController();
  final _password = TextEditingController();
  bool _acceptedTerms = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    if (_name.text.trim().isEmpty || _password.text.length < 12 || !_acceptedTerms) {
      setState(() => _error = 'Enter your name, use at least 12 characters, and accept the terms.');
      return;
    }
    try {
      final registeredEmail = await widget.controller.register(
        invitationToken: widget.invitationToken,
        fullName: _name.text.trim(),
        password: _password.text,
      );
      if (mounted) {
        widget.onCreated(registeredEmail);
        Navigator.pop(context);
      }
    } on ApiException catch (error) {
      setState(() => _error = error.message);
    } catch (_) {
      setState(() => _error = 'Could not reach the server. Try again when online.');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Create account')),
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                Text('Join MediFuel', style: Theme.of(context).textTheme.headlineLarge),
                const SizedBox(height: 8),
                const Text('Your invitation determines your fleet and access role.'),
                const SizedBox(height: 26),
                TextField(controller: _name, decoration: const InputDecoration(labelText: 'Full name')),
                const SizedBox(height: 16),
                TextField(
                  controller: _password,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Password', helperText: 'Use at least 12 characters.'),
                ),
                CheckboxListTile(
                  value: _acceptedTerms,
                  contentPadding: EdgeInsets.zero,
                  onChanged: (value) => setState(() => _acceptedTerms = value ?? false),
                  title: const Text('I agree to the Terms of Use and Privacy Policy.'),
                  controlAffinity: ListTileControlAffinity.leading,
                ),
                if (_error != null) Text(_error!, style: const TextStyle(color: MediFuelColors.red)),
                const SizedBox(height: 16),
                FilledButton(onPressed: _create, child: const Padding(padding: EdgeInsets.all(12), child: Text('Create account'))),
              ],
            ),
          ),
        ),
      );
}

class _BrandLockup extends StatelessWidget {
  const _BrandLockup({this.centered = false});

  final bool centered;

  @override
  Widget build(BuildContext context) {
    final content = Row(
      mainAxisSize: centered ? MainAxisSize.min : MainAxisSize.max,
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(color: MediFuelColors.navy, borderRadius: BorderRadius.circular(13)),
          child: const Icon(Icons.local_hospital, color: Colors.white, size: 28),
        ),
        const SizedBox(width: 12),
        RichText(
          text: const TextSpan(
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: MediFuelColors.navy),
            children: [
              TextSpan(text: 'Medi'),
              TextSpan(text: 'Fuel', style: TextStyle(color: MediFuelColors.orange)),
            ],
          ),
        ),
      ],
    );
    return centered ? Center(child: content) : content;
  }
}