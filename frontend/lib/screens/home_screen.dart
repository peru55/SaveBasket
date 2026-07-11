import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/supermarket_provider.dart';
import 'login_screen.dart';
import '../providers/basket_provider.dart';
import '../services/api_exception.dart';
import '../theme/app_theme.dart';
import 'search_screen.dart';
import 'basket_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<BasketProvider>(context, listen: false).initializeBasket();
      // load supermarkets early so UI can render logos and selectors
      try {
        Provider.of<SupermarketProvider>(context, listen: false).load();
      } catch (_) {}
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<BasketProvider>(context);
    final isWide = MediaQuery.sizeOf(context).width >= 900;
    final tabs = [
      _DashboardTab(
        provider: provider,
        onBrowse: () => setState(() => _currentIndex = 1),
        onBasket: () => setState(() => _currentIndex = 2),
      ),
      const SearchScreen(),
      const BasketScreen(),
    ];

    return Scaffold(
      body: provider.isLoading && provider.activeBasket == null
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.green))
          : SafeArea(
              child: isWide
                  ? Row(
                      children: [
                        _DesktopRail(
                          selectedIndex: _currentIndex,
                          onSelected: (index) =>
                              setState(() => _currentIndex = index),
                        ),
                        Expanded(child: tabs[_currentIndex]),
                      ],
                    )
                  : tabs[_currentIndex],
            ),
      bottomNavigationBar: isWide
          ? null
          : _MobileNavBar(
              selectedIndex: _currentIndex,
              onSelected: (index) => setState(() => _currentIndex = index),
            ),
    );
  }
}

class _MobileNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  const _MobileNavBar({
    required this.selectedIndex,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      decoration: BoxDecoration(
        color: AppColors.deepGreen,
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: AppColors.deepGreen.withOpacity(0.20),
            blurRadius: 24,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(22),
        child: SizedBox(
          height: 68,
          child: Row(
            children: [
              Expanded(
                child: _MobileNavItem(
                  icon: Icons.space_dashboard_outlined,
                  selectedIcon: Icons.space_dashboard_rounded,
                  label: 'Home',
                  selected: selectedIndex == 0,
                  onTap: () => onSelected(0),
                ),
              ),
              Expanded(
                child: _MobileNavItem(
                  icon: Icons.manage_search_rounded,
                  selectedIcon: Icons.manage_search_rounded,
                  label: 'Browse',
                  selected: selectedIndex == 1,
                  onTap: () => onSelected(1),
                ),
              ),
              Expanded(
                child: _MobileNavItem(
                  icon: Icons.shopping_basket_outlined,
                  selectedIcon: Icons.shopping_basket_rounded,
                  label: 'Basket',
                  selected: selectedIndex == 2,
                  onTap: () => onSelected(2),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MobileNavItem extends StatelessWidget {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _MobileNavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Center(
          child: SizedBox(
            width: 76,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  width: 48,
                  height: 28,
                  decoration: BoxDecoration(
                    color: selected ? AppColors.lime : Colors.transparent,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Icon(
                    selected ? selectedIcon : icon,
                    color: selected ? AppColors.deepGreen : Colors.white70,
                    size: 22,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: selected ? AppColors.lime : Colors.white70,
                        fontSize: 11,
                      ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DesktopRail extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  const _DesktopRail({
    required this.selectedIndex,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 118,
      margin: const EdgeInsets.all(18),
      padding: const EdgeInsets.symmetric(vertical: 18),
      decoration: BoxDecoration(
        color: AppColors.deepGreen,
        borderRadius: BorderRadius.circular(30),
        boxShadow: [
          BoxShadow(
            color: AppColors.deepGreen.withOpacity(0.18),
            blurRadius: 30,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      child: Column(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: AppColors.lime,
              borderRadius: BorderRadius.circular(18),
            ),
            child: const Icon(Icons.local_grocery_store_rounded,
                color: AppColors.deepGreen),
          ),
          const SizedBox(height: 28),
          _RailItem(
              icon: Icons.space_dashboard_rounded,
              label: 'Home',
              selected: selectedIndex == 0,
              onTap: () => onSelected(0)),
          _RailItem(
              icon: Icons.manage_search_rounded,
              label: 'Browse',
              selected: selectedIndex == 1,
              onTap: () => onSelected(1)),
          _RailItem(
              icon: Icons.shopping_basket_rounded,
              label: 'Basket',
              selected: selectedIndex == 2,
              onTap: () => onSelected(2)),
          const Spacer(),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(18),
            ),
            child: const Icon(Icons.savings_rounded, color: AppColors.lime),
          ),
        ],
      ),
    );
  }
}

class _RailItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _RailItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: selected ? AppColors.lime : Colors.transparent,
            borderRadius: BorderRadius.circular(18),
          ),
          child: Column(
            children: [
              Icon(icon,
                  color: selected ? AppColors.deepGreen : Colors.white70),
              const SizedBox(height: 5),
              Text(
                label,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: selected ? AppColors.deepGreen : Colors.white70,
                      fontSize: 11,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardTab extends StatelessWidget {
  final BasketProvider provider;
  final VoidCallback onBrowse;
  final VoidCallback onBasket;

  const _DashboardTab({
    required this.provider,
    required this.onBrowse,
    required this.onBasket,
  });

  @override
  Widget build(BuildContext context) {
    if (provider.backendError != null && provider.activeBasket == null) {
      return _OfflineState(provider: provider);
    }

    final basket = provider.activeBasket;
    final comparisons = provider.comparisonResults;
    final bestDeal = comparisons.isNotEmpty ? comparisons.first : null;
    final itemCount =
        basket?.items.fold<int>(0, (sum, item) => sum + item.quantity) ?? 0;
    final uniqueCount = basket?.items.length ?? 0;
    final savings = comparisons.length > 1
        ? (comparisons.last.totalCost - comparisons.first.totalCost)
            .clamp(0.0, double.infinity)
            .toDouble()
        : 0.0;

    return RefreshIndicator(
      color: AppColors.green,
      onRefresh: () => provider.fetchComparison(),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth >= 900;
          return ListView(
            physics: const AlwaysScrollableScrollPhysics(
                parent: BouncingScrollPhysics()),
            padding:
                EdgeInsets.fromLTRB(isWide ? 32 : 20, 18, isWide ? 32 : 20, 28),
            children: [
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1180),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _TopBar(itemCount: itemCount),
                      const SizedBox(height: 18),
                      if (isWide)
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 7,
                              child: _SavingsHero(
                                bestStore: bestDeal == null
                                    ? 'Build your basket'
                                    : bestDeal.supermarketName,
                                branch: bestDeal?.branchName ??
                                    'Compare nearby branches',
                                total: bestDeal?.totalCost,
                                savings: savings,
                                isComplete: bestDeal?.isComplete ?? true,
                              ),
                            ),
                            const SizedBox(width: 18),
                            Expanded(
                              flex: 4,
                              child: _DesktopSummaryPanel(
                                itemCount: itemCount,
                                storeCount: comparisons.length,
                                uniqueCount: uniqueCount,
                                savings: savings,
                                comparisons: comparisons,
                              ),
                            ),
                          ],
                        )
                      else ...[
                        _SavingsHero(
                          bestStore: bestDeal == null
                              ? 'Build your basket'
                              : bestDeal.supermarketName,
                          branch:
                              bestDeal?.branchName ?? 'Compare nearby branches',
                          total: bestDeal?.totalCost,
                          savings: savings,
                          isComplete: bestDeal?.isComplete ?? true,
                        ),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Expanded(
                                child: _MetricCard(
                                    label: 'Items',
                                    value: '$itemCount',
                                    icon: Icons.shopping_bag_rounded)),
                            const SizedBox(width: 12),
                            Expanded(
                                child: _MetricCard(
                                    label: 'Stores',
                                    value: '${comparisons.length}',
                                    icon: Icons.storefront_rounded)),
                            const SizedBox(width: 12),
                            Expanded(
                                child: _MetricCard(
                                    label: 'Lines',
                                    value: '$uniqueCount',
                                    icon: Icons.receipt_long_rounded)),
                          ],
                        ),
                      ],
                      const SizedBox(height: 22),
                      const _SectionHeader(
                          title: 'Fast Actions', trailing: 'Live pricing'),
                      const SizedBox(height: 10),
                      isWide
                          ? Row(
                              children: [
                                Expanded(
                                  child: _ActionTile(
                                    icon: Icons.search_rounded,
                                    title: 'Find products',
                                    subtitle:
                                        'Search staples and compare unit prices',
                                    color: AppColors.green,
                                    onTap: onBrowse,
                                  ),
                                ),
                                const SizedBox(width: 14),
                                Expanded(
                                  child: _ActionTile(
                                    icon: Icons.compare_arrows_rounded,
                                    title: 'Optimize trip',
                                    subtitle: 'Rank stores by basket total',
                                    color: AppColors.deepGreen,
                                    onTap: onBasket,
                                  ),
                                ),
                                const SizedBox(width: 14),
                                Expanded(
                                  child: _ActionTile(
                                    icon: Icons.storefront_rounded,
                                    title: 'Track stores',
                                    subtitle:
                                        'See complete and partial baskets',
                                    color: AppColors.amber,
                                    onTap: onBasket,
                                  ),
                                ),
                              ],
                            )
                          : Row(
                              children: [
                                Expanded(
                                  child: _ActionTile(
                                    icon: Icons.search_rounded,
                                    title: 'Find products',
                                    subtitle:
                                        'Search staples and compare unit prices',
                                    color: AppColors.green,
                                    onTap: onBrowse,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: _ActionTile(
                                    icon: Icons.compare_arrows_rounded,
                                    title: 'Optimize trip',
                                    subtitle: 'Rank stores by basket total',
                                    color: AppColors.deepGreen,
                                    onTap: onBasket,
                                  ),
                                ),
                              ],
                            ),
                      const SizedBox(height: 22),
                      const _SectionHeader(
                          title: 'Market Pulse', trailing: 'Nairobi'),
                      const SizedBox(height: 10),
                      _MarketPulse(comparisons: comparisons, savings: savings),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _DesktopSummaryPanel extends StatelessWidget {
  final int itemCount;
  final int storeCount;
  final int uniqueCount;
  final double savings;
  final List comparisons;

  const _DesktopSummaryPanel({
    required this.itemCount,
    required this.storeCount,
    required this.uniqueCount,
    required this.savings,
    required this.comparisons,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                  child: _MetricCard(
                      label: 'Items',
                      value: '$itemCount',
                      icon: Icons.shopping_bag_rounded)),
              const SizedBox(width: 10),
              Expanded(
                  child: _MetricCard(
                      label: 'Stores',
                      value: '$storeCount',
                      icon: Icons.storefront_rounded)),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                  child: _MetricCard(
                      label: 'Lines',
                      value: '$uniqueCount',
                      icon: Icons.receipt_long_rounded)),
              const SizedBox(width: 10),
              Expanded(
                  child: _MetricCard(
                      label: 'Saved',
                      value: 'KSh ${savings.toStringAsFixed(0)}',
                      icon: Icons.savings_rounded)),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.mint,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Text(
              comparisons.length > 1
                  ? 'Best price is active across ranked stores.'
                  : 'Add items to activate the savings engine.',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class _MarketPulse extends StatelessWidget {
  final List comparisons;
  final double savings;

  const _MarketPulse({required this.comparisons, required this.savings});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      color: AppColors.mint,
      border: Border.all(color: AppColors.green.withOpacity(0.16)),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.bolt_rounded, color: AppColors.amber),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              comparisons.length > 1
                  ? 'Switching to ${comparisons.first.supermarketName} could keep KSh ${savings.toStringAsFixed(0)} in your pocket today.'
                  : 'Add milk, flour, sugar, or rice to start seeing store-by-store savings.',
              style: Theme.of(context)
                  .textTheme
                  .bodyLarge
                  ?.copyWith(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  final int itemCount;

  const _TopBar({required this.itemCount});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: AppColors.deepGreen,
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Icon(Icons.local_grocery_store_rounded,
              color: AppColors.lime),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('SaveBasket', style: Theme.of(context).textTheme.titleLarge),
              Text('Smart grocery savings',
                  style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: AppColors.line),
              ),
              child: Row(
                children: [
                  const Icon(Icons.location_on_rounded,
                      color: AppColors.green, size: 16),
                  const SizedBox(width: 4),
                  Text('Nairobi',
                      style: Theme.of(context).textTheme.labelLarge),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: AppColors.line),
              ),
              child: IconButton(
                icon: const Icon(Icons.logout, color: AppColors.green),
                onPressed: () async {
                  final auth =
                      Provider.of<AuthProvider>(context, listen: false);
                  await auth.logout();
                  if (!context.mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Logged out')));
                  await Future.delayed(const Duration(milliseconds: 300));
                  if (!context.mounted) return;
                  Navigator.of(context).pushAndRemoveUntil(
                      MaterialPageRoute(builder: (_) => const LoginScreen()),
                      (r) => false);
                },
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _SavingsHero extends StatelessWidget {
  final String bestStore;
  final String branch;
  final double? total;
  final double savings;
  final bool isComplete;

  const _SavingsHero({
    required this.bestStore,
    required this.branch,
    required this.total,
    required this.savings,
    required this.isComplete,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: AppColors.deepGreen,
        borderRadius: BorderRadius.circular(26),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth >= 640;
          return Row(
            children: [
              Expanded(
                flex: 3,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        _StatusPill(
                            label: isComplete
                                ? 'Best full basket'
                                : 'Partial basket',
                            color:
                                isComplete ? AppColors.lime : AppColors.amber),
                        const Spacer(),
                        const Icon(Icons.trending_down_rounded,
                            color: AppColors.lime),
                      ],
                    ),
                    SizedBox(height: isWide ? 38 : 24),
                    Text(
                      total == null
                          ? 'Start saving on your next shop'
                          : 'KSh ${total!.toStringAsFixed(0)}',
                      style: Theme.of(context)
                          .textTheme
                          .headlineLarge
                          ?.copyWith(
                              color: Colors.white, fontSize: isWide ? 44 : 36),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '$bestStore • $branch',
                      style: Theme.of(context)
                          .textTheme
                          .bodyLarge
                          ?.copyWith(color: Colors.white.withOpacity(0.78)),
                    ),
                    const SizedBox(height: 18),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(16),
                        border:
                            Border.all(color: Colors.white.withOpacity(0.12)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.savings_rounded,
                              color: AppColors.lime, size: 20),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              savings > 0
                                  ? 'Potential savings: KSh ${savings.toStringAsFixed(0)}'
                                  : 'Compare supermarkets before checkout',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(color: Colors.white),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              if (isWide) ...[
                const SizedBox(width: 22),
                Expanded(
                  flex: 2,
                  child: Container(
                    height: 220,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: Colors.white.withOpacity(0.12)),
                    ),
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        Positioned(
                          right: 24,
                          bottom: 18,
                          child: Icon(Icons.shopping_basket_rounded,
                              size: 146,
                              color: AppColors.lime.withOpacity(0.24)),
                        ),
                        const Positioned(
                          top: 38,
                          left: 34,
                          child: Icon(Icons.eco_rounded,
                              size: 58, color: AppColors.lime),
                        ),
                        Positioned(
                          right: 34,
                          top: 44,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 8),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text('Live prices',
                                style: Theme.of(context)
                                    .textTheme
                                    .labelLarge
                                    ?.copyWith(color: AppColors.deepGreen)),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;

  const _MetricCard(
      {required this.label, required this.value, required this.icon});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppColors.green, size: 20),
          const SizedBox(height: 12),
          Text(value, style: Theme.of(context).textTheme.titleLarge),
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  const _ActionTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadii.large),
        onTap: onTap,
        child: AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: color),
              ),
              const SizedBox(height: 16),
              Text(title, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final String trailing;

  const _SectionHeader({required this.title, required this.trailing});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(title, style: Theme.of(context).textTheme.titleLarge),
        const Spacer(),
        Text(trailing,
            style: Theme.of(context)
                .textTheme
                .labelLarge
                ?.copyWith(color: AppColors.green)),
      ],
    );
  }
}

class _StatusPill extends StatelessWidget {
  final String label;
  final Color color;

  const _StatusPill({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context)
            .textTheme
            .labelLarge
            ?.copyWith(color: AppColors.deepGreen),
      ),
    );
  }
}

class _OfflineState extends StatelessWidget {
  final BasketProvider provider;

  const _OfflineState({required this.provider});

  @override
  Widget build(BuildContext context) {
    final error = provider.backendError!;
    final isAuthentication = error.kind == ApiErrorKind.authentication;
    final isConnection = error.kind == ApiErrorKind.connection;
    final icon = isAuthentication
        ? Icons.lock_clock_rounded
        : isConnection
            ? Icons.cloud_off_rounded
            : Icons.warning_amber_rounded;
    final actionLabel = isAuthentication
        ? 'Sign in again'
        : isConnection
            ? 'Reconnect'
            : 'Try again';
    final actionIcon =
        isAuthentication ? Icons.login_rounded : Icons.refresh_rounded;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: AppCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 52, color: AppColors.coral),
              const SizedBox(height: 14),
              Text(error.title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                error.message,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: isAuthentication
                    ? () async {
                        await context.read<AuthProvider>().logout();
                      }
                    : provider.initializeBasket,
                icon: Icon(actionIcon),
                label: Text(actionLabel),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
