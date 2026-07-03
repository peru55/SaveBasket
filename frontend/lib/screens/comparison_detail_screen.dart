import 'package:flutter/material.dart';
import '../models/basket.dart';
import '../theme/app_theme.dart';

class ComparisonDetailScreen extends StatelessWidget {
  final BasketComparisonResult result;
  final Basket basket;

  const ComparisonDetailScreen({
    super.key,
    required this.result,
    required this.basket,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Store breakdown'),
      ),
      body: ListView(
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: [
          AppCard(
            color: AppColors.deepGreen,
            border: Border.all(color: AppColors.deepGreen),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 50,
                      height: 50,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: Padding(
                          padding: const EdgeInsets.all(6),
                          child: _StoreLogo(result: result),
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(result.supermarketName,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.copyWith(color: Colors.white)),
                          const SizedBox(height: 3),
                          Text('${result.branchName} Branch',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(color: Colors.white70)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                Row(
                  children: [
                    Expanded(
                      child: _SummaryStat(
                        label: 'Total estimate',
                        value: 'KSh ${result.totalCost.toStringAsFixed(0)}',
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _SummaryStat(
                        label: 'Available',
                        value: '${result.itemsAvailable}/${result.totalItems}',
                      ),
                    ),
                  ],
                ),
                if (!result.isComplete) ...[
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.amberSoft,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.warning_amber_rounded,
                            color: AppColors.amber),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'This branch is missing some items, so the total only includes available products.',
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(color: AppColors.ink),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 22),
          Text('Receipt preview',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          ..._breakdownRows().map((item) => _BreakdownRow(item: item)),
        ],
      ),
    );
  }

  List<BasketProductBreakdown> _breakdownRows() {
    if (result.productBreakdown.isNotEmpty) {
      return result.productBreakdown;
    }

    return basket.items.map((basketItem) {
      final isMissing = result.missingItems
          .any((missing) => missing['id'] == basketItem.product.id);
      return BasketProductBreakdown(
        id: basketItem.product.id,
        name: basketItem.product.name,
        quantity: basketItem.quantity,
        unitPrice: null,
        subtotal: 0,
        inStock: !isMissing,
      );
    }).toList();
  }
}

class _StoreLogo extends StatelessWidget {
  final BasketComparisonResult result;

  const _StoreLogo({required this.result});

  @override
  Widget build(BuildContext context) {
    final localAsset = result.localLogoAsset;

    if (localAsset != null) {
      return Image.asset(
        localAsset,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) =>
            const Icon(Icons.storefront_rounded, color: AppColors.green),
      );
    }

    if (result.logoUrl != null) {
      return Image.network(
        result.logoUrl!,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) =>
            const Icon(Icons.storefront_rounded, color: AppColors.green),
      );
    }

    return const Icon(Icons.storefront_rounded, color: AppColors.green);
  }
}

class _SummaryStat extends StatelessWidget {
  final String label;
  final String value;

  const _SummaryStat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: Colors.white70)),
          const SizedBox(height: 5),
          Text(value,
              style: Theme.of(context)
                  .textTheme
                  .titleLarge
                  ?.copyWith(color: AppColors.lime)),
        ],
      ),
    );
  }
}

class _BreakdownRow extends StatelessWidget {
  final BasketProductBreakdown item;

  const _BreakdownRow({required this.item});

  @override
  Widget build(BuildContext context) {
    final isMissing = !item.inStock;
    final unitPriceText = item.unitPrice == null
        ? 'Unavailable'
        : 'KSh ${item.unitPrice!.toStringAsFixed(0)} each';
    final subtotalText =
        item.inStock ? 'KSh ${item.subtotal.toStringAsFixed(0)}' : 'KSh 0';

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AppCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: isMissing ? AppColors.amberSoft : AppColors.mint,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(
                    isMissing
                        ? Icons.remove_shopping_cart_outlined
                        : Icons.check_rounded,
                    color: isMissing ? AppColors.amber : AppColors.green,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    item.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: isMissing ? AppColors.amberSoft : AppColors.mint,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    isMissing ? 'Missing' : 'In stock',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: isMissing ? AppColors.amber : AppColors.green,
                          fontSize: 11,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _PriceCell(label: 'Qty', value: '${item.quantity}'),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _PriceCell(label: 'Unit price', value: unitPriceText),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _PriceCell(label: 'Subtotal', value: subtotalText),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _PriceCell extends StatelessWidget {
  final String label;
  final String value;

  const _PriceCell({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
      decoration: BoxDecoration(
        color: AppColors.canvas,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: AppColors.muted,
                  fontSize: 11,
                ),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.ink,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}
