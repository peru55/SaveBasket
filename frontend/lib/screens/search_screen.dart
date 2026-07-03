import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/product.dart';
import '../providers/basket_provider.dart';
import '../theme/app_theme.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  final List<String> _suggestions = const ['milk', 'sugar', 'flour', 'rice'];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<BasketProvider>(context);
    final products = provider.searchResults;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth >= 900;
        return Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1180),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: EdgeInsets.fromLTRB(
                      isWide ? 32 : 20, 18, isWide ? 32 : 20, 12),
                  child: AppCard(
                    padding: EdgeInsets.all(isWide ? 22 : 16),
                    color: isWide ? AppColors.deepGreen : Colors.white,
                    border: Border.all(
                        color: isWide ? AppColors.deepGreen : AppColors.line),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Browse groceries',
                                    style: Theme.of(context)
                                        .textTheme
                                        .headlineMedium
                                        ?.copyWith(
                                          color: isWide
                                              ? Colors.white
                                              : AppColors.ink,
                                        ),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    'Search staples and add them to your savings basket.',
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodyMedium
                                        ?.copyWith(
                                          color: isWide
                                              ? Colors.white70
                                              : AppColors.muted,
                                        ),
                                  ),
                                ],
                              ),
                            ),
                            if (isWide)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 12, vertical: 8),
                                decoration: BoxDecoration(
                                  color: AppColors.lime,
                                  borderRadius: BorderRadius.circular(999),
                                ),
                                child: Text(
                                  'Nairobi prices',
                                  style: Theme.of(context)
                                      .textTheme
                                      .labelLarge
                                      ?.copyWith(color: AppColors.deepGreen),
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _searchController,
                          onChanged: (value) {
                            setState(() {});
                            provider.searchProducts(value);
                          },
                          textInputAction: TextInputAction.search,
                          decoration: InputDecoration(
                            hintText: 'Search milk, sugar, flour...',
                            prefixIcon: const Icon(Icons.search_rounded,
                                color: AppColors.green),
                            suffixIcon: _searchController.text.isNotEmpty
                                ? IconButton(
                                    icon: const Icon(Icons.close_rounded),
                                    onPressed: () {
                                      _searchController.clear();
                                      provider.searchProducts('');
                                      setState(() {});
                                    },
                                  )
                                : null,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: _suggestions.map((term) {
                            return ActionChip(
                              label: Text(term),
                              avatar: const Icon(Icons.add_rounded, size: 16),
                              backgroundColor: Colors.white,
                              side: BorderSide(
                                  color:
                                      isWide ? Colors.white : AppColors.line),
                              labelStyle: const TextStyle(
                                  color: AppColors.ink,
                                  fontWeight: FontWeight.w700),
                              onPressed: () {
                                _searchController.text = term;
                                provider.searchProducts(term);
                                setState(() {});
                              },
                            );
                          }).toList(),
                        ),
                      ],
                    ),
                  ),
                ),
                Expanded(
                  child: provider.isLoading
                      ? const Center(
                          child:
                              CircularProgressIndicator(color: AppColors.green))
                      : _searchController.text.isEmpty
                          ? const _SearchState(
                              icon: Icons.manage_search_rounded,
                              title: 'Start with a pantry staple',
                              body:
                                  'Try milk, sugar, rice, flour, or maize meal.',
                            )
                          : products.isEmpty
                              ? const _SearchState(
                                  icon: Icons.search_off_rounded,
                                  title: 'No match yet',
                                  body:
                                      'Try a shorter product name or another category.',
                                )
                              : _ProductList(
                                  products: products,
                                  provider: provider,
                                  isWide: isWide),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ProductList extends StatelessWidget {
  final List<Product> products;
  final BasketProvider provider;
  final bool isWide;

  const _ProductList({
    required this.products,
    required this.provider,
    required this.isWide,
  });

  @override
  Widget build(BuildContext context) {
    if (isWide) {
      return GridView.builder(
        padding: const EdgeInsets.fromLTRB(32, 4, 32, 24),
        physics: const BouncingScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
          maxCrossAxisExtent: 360,
          mainAxisExtent: 118,
          crossAxisSpacing: 14,
          mainAxisSpacing: 14,
        ),
        itemCount: products.length,
        itemBuilder: (context, index) =>
            _buildProduct(context, products[index]),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
      physics: const BouncingScrollPhysics(),
      itemCount: products.length,
      itemBuilder: (context, index) => _buildProduct(context, products[index]),
    );
  }

  Widget _buildProduct(BuildContext context, Product product) {
    final isInBasket = provider.activeBasket?.items
            .any((item) => item.product.id == product.id) ??
        false;
    return _ProductRow(
      product: product,
      isInBasket: isInBasket,
      onAdd: () {
        if (isInBasket) {
          final item = provider.activeBasket?.items
              .firstWhere((i) => i.product.id == product.id);
          if (item != null) {
            provider.updateQuantity(product.id, item.quantity + 1);
          }
        } else {
          provider.addItem(product);
        }

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${product.name} added to basket')),
        );
      },
    );
  }
}

class _ProductRow extends StatelessWidget {
  final Product product;
  final bool isInBasket;
  final VoidCallback onAdd;

  const _ProductRow({
    required this.product,
    required this.isInBasket,
    required this.onAdd,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: AppCard(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Container(
                width: 58,
                height: 58,
                color: AppColors.mint,
                child: product.imageUrl != null
                    ? Image.network(
                        product.imageUrl!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const Icon(
                            Icons.shopping_bag_outlined,
                            color: AppColors.green),
                      )
                    : const Icon(Icons.shopping_bag_outlined,
                        color: AppColors.green),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.name,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    '${product.brand ?? "Generic"} • ${product.category ?? "Pantry"}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            IconButton.filled(
              onPressed: onAdd,
              style: IconButton.styleFrom(
                backgroundColor: isInBasket ? AppColors.green : AppColors.mint,
                foregroundColor: isInBasket ? Colors.white : AppColors.green,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14)),
              ),
              icon:
                  Icon(isInBasket ? Icons.add_task_rounded : Icons.add_rounded),
              tooltip: 'Add to basket',
            ),
          ],
        ),
      ),
    );
  }
}

class _SearchState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String body;

  const _SearchState({
    required this.icon,
    required this.title,
    required this.body,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 58, color: AppColors.green.withOpacity(0.34)),
            const SizedBox(height: 14),
            Text(title,
                style: Theme.of(context).textTheme.titleLarge,
                textAlign: TextAlign.center),
            const SizedBox(height: 6),
            Text(body,
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
