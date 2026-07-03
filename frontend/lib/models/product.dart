class Product {
  final String id;
  final String name;
  final String? sku;
  final String? barcode;
  final String? category;
  final String? brand;
  final String? imageUrl;
  final String? description;

  Product({
    required this.id,
    required this.name,
    this.sku,
    this.barcode,
    this.category,
    this.brand,
    this.imageUrl,
    this.description,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'],
      name: json['name'],
      sku: json['sku'],
      barcode: json['barcode'],
      category: json['category'],
      brand: json['brand'],
      imageUrl: json['image_url'],
      description: json['description'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'sku': sku,
      'barcode': barcode,
      'category': category,
      'brand': brand,
      'image_url': imageUrl,
      'description': description,
    };
  }
}

class ProductPrice {
  final String id;
  final String productId;
  final String branchId;
  final String branchName;
  final String supermarketName;
  final double price;
  final DateTime updatedAt;
  final String? sourceUrl;

  ProductPrice({
    required this.id,
    required this.productId,
    required this.branchId,
    required this.branchName,
    required this.supermarketName,
    required this.price,
    required this.updatedAt,
    this.sourceUrl,
  });

  factory ProductPrice.fromJson(Map<String, dynamic> json) {
    return ProductPrice(
      id: json['id'],
      productId: json['product_id'] ?? '',
      branchId: json['branch']['id'] ?? json['branch_id'] ?? '',
      branchName: json['branch']['name'] ?? json['branch_name'] ?? '',
      supermarketName: json['branch']['supermarket_name'] ?? json['supermarket_name'] ?? '',
      price: double.parse(json['price'].toString()),
      updatedAt: DateTime.parse(json['updated_at']),
      sourceUrl: json['source_url'],
    );
  }
}
