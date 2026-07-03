import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/basket.dart';
import '../providers/basket_provider.dart';
import '../theme/app_theme.dart';
import 'comparison_detail_screen.dart';

class BasketScreen extends StatelessWidget {
  const BasketScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<BasketProvider>(context);
    final basket = provider.activeBasket;
    final items = basket?.items ?? [];
    final comparisons = provider.comparisonResults;
    final bestDeal = comparisons.isNotEmpty ? comparisons.first : null;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth >= 900;
        final header = Padding(
          padding:
              EdgeInsets.fromLTRB(isWide ? 32 : 20, 18, isWide ? 32 : 20, 12),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1180),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Savings basket',
                          style: Theme.of(context).textTheme.headlineMedium),
                      const SizedBox(height: 6),
                      Text('${items.length} grocery lines ready to optimize',
                          style: Theme.of(context).textTheme.bodyMedium),
                    ],
                  ),
                ),
                IconButton.filledTonal(
                  onPressed: items.isEmpty ? null : provider.fetchComparison,
                  icon: const Icon(Icons.sync_rounded),
                  tooltip: 'Refresh prices',
                ),
              ],
            ),
          ),
        );

        return Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            header,
            Expanded(
              child: items.isEmpty
                  ? const _EmptyBasket()
                  : Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1180),
                        child: isWide
                            ? Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    flex: 5,
                                    child: ListView(
                                      physics: const BouncingScrollPhysics(),
                                      padding: const EdgeInsets.fromLTRB(
                                          32, 4, 10, 24),
                                      children: [
                                        if (bestDeal != null)
                                          _BestDealSummary(result: bestDeal),
                                        const SizedBox(height: 14),
                                        Text('Items',
                                            style: Theme.of(context)
                                                .textTheme
                                                .titleLarge),
                                        const SizedBox(height: 10),
                                        ...items.map((item) => _BasketItemRow(
                                            item: item, provider: provider)),
                                      ],
                                    ),
                                  ),
                                  Expanded(
                                    flex: 6,
                                    child: ListView(
                                      physics: const BouncingScrollPhysics(),
                                      padding: const EdgeInsets.fromLTRB(
                                          10, 4, 32, 24),
                                      children: [
                                        Row(
                                          children: [
                                            Text('Store comparison',
                                                style: Theme.of(context)
                                                    .textTheme
                                                    .titleLarge),
                                            const Spacer(),
                                            const Icon(Icons.bolt_rounded,
                                                color: AppColors.amber,
                                                size: 18),
                                          ],
                                        ),
                                        const SizedBox(height: 10),
                                        _ComparisonResults(
                                            provider: provider,
                                            comparisons: comparisons,
                                            basket: basket!),
                                      ],
                                    ),
                                  ),
                                ],
                              )
                            : ListView(
                                physics: const BouncingScrollPhysics(),
                                padding:
                                    const EdgeInsets.fromLTRB(20, 4, 20, 24),
                                children: [
                                  if (bestDeal != null)
                                    _BestDealSummary(result: bestDeal),
                                  const SizedBox(height: 14),
                                  Text('Items',
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleLarge),
                                  const SizedBox(height: 10),
                                  ...items.map((item) => _BasketItemRow(
                                      item: item, provider: provider)),
                                  const SizedBox(height: 14),
                                  Row(
                                    children: [
                                      Text('Store comparison',
                                          style: Theme.of(context)
                                              .textTheme
                                              .titleLarge),
                                      const Spacer(),
                                      const Icon(Icons.bolt_rounded,
                                          color: AppColors.amber, size: 18),
                                    ],
                                  ),
                                  const SizedBox(height: 10),
                                  _ComparisonResults(
                                      provider: provider,
                                      comparisons: comparisons,
                                      basket: basket!),
                                ],
                              ),
                      ),
                    ),
            ),
          ],
        );
      },
    );
  }
}

class _ComparisonResults extends StatelessWidget {
  final BasketProvider provider;
  final List<BasketComparisonResult> comparisons;
  final Basket basket;

  const _ComparisonResults({
    required this.provider,
    required this.comparisons,
    required this.basket,
  });

  @override
  Widget build(BuildContext context) {
    if (provider.isLoading) {
      return const Padding(
        padding: EdgeInsets.all(28),
        child: Center(child: CircularProgressIndicator(color: AppColors.green)),
      );
    }

    if (comparisons.isEmpty) {
      return const _NoPrices();
    }

    return Column(
      children: comparisons.asMap().entries.map((entry) {
        return _ComparisonTile(
          result: entry.value,
          basket: basket,
          rank: entry.key + 1,
          isBest: entry.key == 0,
        );
      }).toList(),
    );
  }
}

class _BestDealSummary extends StatelessWidget {
  final BasketComparisonResult result;

  const _BestDealSummary({required this.result});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      color: AppColors.deepGreen,
      border: Border.all(color: AppColors.deepGreen),
      child: Row(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: AppColors.lime,
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(Icons.workspace_premium_rounded,
                color: AppColors.deepGreen),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Best current basket',
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium
                        ?.copyWith(color: Colors.white70)),
                const SizedBox(height: 3),
                Text(
                  '${result.supermarketName} • ${result.branchName}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(color: Colors.white),
                ),
              ],
            ),
          ),
          Text(
            'KSh ${result.totalCost.toStringAsFixed(0)}',
            style: Theme.of(context)
                .textTheme
                .titleLarge
                ?.copyWith(color: AppColors.lime),
          ),
        ],
      ),
    );
  }
}

class _BasketItemRow extends StatelessWidget {
  final BasketItem item;
  final BasketProvider provider;

  const _BasketItemRow({required this.item, required this.provider});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AppCard(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: AppColors.mint,
                borderRadius: BorderRadius.circular(14),
              ),
              child: item.product.imageUrl != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: Image.network(
                        item.product.imageUrl!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const Icon(
                            Icons.shopping_bag_outlined,
                            color: AppColors.green),
                      ),
                    )
                  : const Icon(Icons.shopping_bag_outlined,
                      color: AppColors.green),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.product.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(item.product.brand ?? 'Generic',
                      style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
            ),
            _QtyButton(
              icon: Icons.remove_rounded,
              onTap: () {
                if (item.quantity > 1) {
                  provider.updateQuantity(item.product.id, item.quantity - 1);
                } else {
                  provider.removeItem(item.product.id);
                }
              },
            ),
            SizedBox(
              width: 30,
              child: Text(
                '${item.quantity}',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            _QtyButton(
              icon: Icons.add_rounded,
              color: AppColors.green,
              onTap: () =>
                  provider.updateQuantity(item.product.id, item.quantity + 1),
            ),
          ],
        ),
      ),
    );
  }
}

class _ComparisonTile extends StatelessWidget {
  final BasketComparisonResult result;
  final Basket basket;
  final int rank;
  final bool isBest;

  const _ComparisonTile({
    required this.result,
    required this.basket,
    required this.rank,
    required this.isBest,
  });

  @override
  Widget build(BuildContext context) {
    final statusColor = result.isComplete ? AppColors.green : AppColors.amber;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadii.large),
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (_) =>
                      ComparisonDetailScreen(result: result, basket: basket)),
            );
          },
          child: AppCard(
            border: Border.all(
                color: isBest ? AppColors.green : AppColors.line,
                width: isBest ? 1.6 : 1),
            child: Row(
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                        color: isBest ? AppColors.green : AppColors.line),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(13),
                    child: Padding(
                      padding: const EdgeInsets.all(5),
                      child: _StoreLogo(result: result),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(result.supermarketName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 3),
                      Text(
                          '#$rank • ${result.branchName} • ${result.itemsAvailable}/${result.totalItems} items',
                          style: Theme.of(context).textTheme.bodyMedium),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('KSh ${result.totalCost.toStringAsFixed(0)}',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        result.isComplete ? 'Complete' : 'Partial',
                        style: Theme.of(context)
                            .textTheme
                            .labelLarge
                            ?.copyWith(color: statusColor, fontSize: 11),
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 4),
                const Icon(Icons.chevron_right_rounded, color: AppColors.muted),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StoreLogo extends StatelessWidget {
  final BasketComparisonResult result;

  const _StoreLogo({required this.result});

  @override
  Widget build(BuildContext context) {
    // Prefer logoUrl, fall back to known local assets via SupermarketProvider
    if (result.logoUrl != null) {
      return Image.network(
        result.logoUrl!,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) =>
            const Icon(Icons.storefront_rounded, color: AppColors.green),
      );
    }

    final localAsset = result.localLogoAsset;
    if (localAsset != null) {
      return Image.asset(
        localAsset,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) =>
            const Icon(Icons.storefront_rounded, color: AppColors.green),
      );
    }

    return const Icon(Icons.storefront_rounded, color: AppColors.green);
  }
}

class _QtyButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  final Color color;

  const _QtyButton({
    required this.icon,
    required this.onTap,
    this.color = AppColors.muted,
  });

  @override
  Widget build(BuildContext context) {
    return IconButton(
      constraints: const BoxConstraints.tightFor(width: 34, height: 34),
      padding: EdgeInsets.zero,
      onPressed: onTap,
      icon: Icon(icon, size: 18, color: color),
      style: IconButton.styleFrom(
        backgroundColor: AppColors.canvas,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}

class _EmptyBasket extends StatelessWidget {
  const _EmptyBasket();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.shopping_basket_outlined,
                size: 64, color: AppColors.green.withOpacity(0.34)),
            const SizedBox(height: 14),
            Text('Your basket is empty',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(
                'Add groceries from Browse to unlock store-by-store price rankings.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}

class _NoPrices extends StatelessWidget {
  const _NoPrices();

  @override
  Widget build(BuildContext context) {
    return const AppCard(
      child: Row(
        children: [
          Icon(Icons.price_change_outlined, color: AppColors.amber),
          SizedBox(width: 12),
          Expanded(child: Text('No store offers found for this basket yet.')),
        ],
      ),
    );
  }
}
