import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/supermarket_provider.dart';
import '../theme/app_theme.dart';

class SupermarketsScreen extends StatelessWidget {
  const SupermarketsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SupermarketProvider>(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Supermarkets')),
      body: RefreshIndicator(
        onRefresh: () => provider.load(),
        child: provider.isLoading
            ? const Center(
                child: CircularProgressIndicator(color: AppColors.green))
            : provider.error != null
                ? Center(child: Text('Error: ${provider.error}'))
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: provider.items.length,
                    itemBuilder: (context, index) {
                      final s = provider.items[index];
                      final localLogoAsset = provider.assetForName(s.name);
                      return ListTile(
                        leading: s.logoUrl != null
                            ? Image.network(s.logoUrl!,
                                width: 48, height: 48, fit: BoxFit.cover)
                            : localLogoAsset != null
                                ? Image.asset(localLogoAsset,
                                    width: 48, height: 48, fit: BoxFit.contain)
                                : const Icon(Icons.storefront_rounded,
                                    color: AppColors.green),
                        title: Text(s.name),
                        subtitle: Text('ID: ${s.id}'),
                      );
                    },
                  ),
      ),
    );
  }
}
