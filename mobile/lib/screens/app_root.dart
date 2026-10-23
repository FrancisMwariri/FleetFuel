import 'package:flutter/material.dart';

import '../data/app_controller.dart';
import 'home_shell.dart';
import 'sign_in_screen.dart';

class AppRoot extends StatelessWidget {
  const AppRoot({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: controller,
        builder: (context, _) {
          if (!controller.initialized) {
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          if (controller.user == null) return SignInScreen(controller: controller);
          return HomeShell(controller: controller);
        },
      );
}