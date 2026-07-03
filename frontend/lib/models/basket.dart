import 'product.dart';

class BasketItem {
  final String id;
  final Product product;
  int quantity;

  BasketItem({
    required this.id,
    required this.product,
    this.quantity = 1,
  });

  factory BasketItem.fromJson(Map<String, dynamic> json) {
    return BasketItem(
      id: json['id'],
      product: Product.fromJson(json['product']),
      quantity: json['quantity'] ?? 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'product': product.toJson(),
      'quantity': quantity,
    };
  }
}

class Basket {
  final String id;
  final String name;
  final List<BasketItem> items;
  final DateTime createdAt;

  Basket({
    required this.id,
    required this.name,
    required this.items,
    required this.createdAt,
  });

  factory Basket.fromJson(Map<String, dynamic> json) {
    var itemsList = json['items'] as List? ?? [];
    List<BasketItem> parsedItems =
        itemsList.map((i) => BasketItem.fromJson(i)).toList();

    return Basket(
      id: json['id'],
      name: json['name'] ?? 'My Basket',
      items: parsedItems,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
    );
  }
}

class BasketComparisonResult {
  final String branchId;
  final String branchName;
  final String supermarketName;
  final String? logoUrl;
  final double totalCost;
  final int itemsAvailable;
  final int totalItems;
  final bool isComplete;
  final List<Map<String, dynamic>> missingItems;
  final List<BasketProductBreakdown> productBreakdown;
  final double? latitude;
  final double? longitude;

  BasketComparisonResult({
    required this.branchId,
    required this.branchName,
    required this.supermarketName,
    this.logoUrl,
    required this.totalCost,
    required this.itemsAvailable,
    required this.totalItems,
    required this.isComplete,
    required this.missingItems,
    required this.productBreakdown,
    this.latitude,
    this.longitude,
  });

  factory BasketComparisonResult.fromJson(Map<String, dynamic> json) {
    return BasketComparisonResult(
      branchId: json['branch_id'],
      branchName: json['branch_name'],
      supermarketName: json['supermarket_name'],
      logoUrl: json['logo_url'],
      totalCost: double.parse(json['total_cost'].toString()),
      itemsAvailable: json['items_available'] ?? 0,
      totalItems: json['total_items'] ?? 0,
      isComplete: json['is_complete'] ?? false,
      missingItems:
          List<Map<String, dynamic>>.from(json['missing_items'] ?? []),
      productBreakdown: (json['product_breakdown'] as List? ?? [])
          .map((item) => BasketProductBreakdown.fromJson(item))
          .toList(),
      latitude: json['latitude'] != null
          ? double.tryParse(json['latitude'].toString())
          : null,
      longitude: json['longitude'] != null
          ? double.tryParse(json['longitude'].toString())
          : null,
    );
  }

  String? get localLogoAsset {
    final normalizedName = supermarketName.toLowerCase();

    if (normalizedName.contains('carrefour')) {
      return 'assets/logos/Carrefour-Logo.png';
    }
    if (normalizedName.contains('naivas')) {
      return 'assets/logos/Naivas-Logo.png';
    }
    if (normalizedName.contains('quickmart')) {
      return 'assets/logos/Quickmart-Logo.jpeg';
    }
    if (normalizedName.contains('cleanshelf') ||
        normalizedName.contains('clean shelf')) {
      return 'assets/logos/Cleanshelf-Logo.jpeg';
    }
    if (normalizedName.contains('eastmatt') ||
        normalizedName.contains('east matt')) {
      return 'assets/logos/Eastmatt-Logo.png';
    }

    return null;
  }
}

class BasketProductBreakdown {
  final String id;
  final String name;
  final int quantity;
  final double? unitPrice;
  final double subtotal;
  final bool inStock;

  BasketProductBreakdown({
    required this.id,
    required this.name,
    required this.quantity,
    required this.unitPrice,
    required this.subtotal,
    required this.inStock,
  });

  factory BasketProductBreakdown.fromJson(Map<String, dynamic> json) {
    final rawUnitPrice = json['unit_price'];
    return BasketProductBreakdown(
      id: json['id'],
      name: json['name'],
      quantity: json['quantity'] ?? 0,
      unitPrice: rawUnitPrice == null
          ? null
          : double.tryParse(rawUnitPrice.toString()),
      subtotal: double.tryParse((json['subtotal'] ?? 0).toString()) ?? 0,
      inStock: json['in_stock'] ?? false,
    );
  }
}
