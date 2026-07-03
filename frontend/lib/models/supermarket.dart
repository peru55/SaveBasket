class Supermarket {
  final String id;
  final String name;
  final String? logoUrl;

  Supermarket({
    required this.id,
    required this.name,
    this.logoUrl,
  });

  factory Supermarket.fromJson(Map<String, dynamic> json) {
    return Supermarket(
      id: json['id'],
      name: json['name'],
      logoUrl: json['logo_url'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'logo_url': logoUrl,
    };
  }
}

class Branch {
  final String id;
  final String supermarketId;
  final String supermarketName;
  final String name;
  final double? latitude;
  final double? longitude;
  final String city;
  final String? address;

  Branch({
    required this.id,
    required this.supermarketId,
    required this.supermarketName,
    required this.name,
    this.latitude,
    this.longitude,
    required this.city,
    this.address,
  });

  factory Branch.fromJson(Map<String, dynamic> json) {
    return Branch(
      id: json['id'],
      supermarketId: json['supermarket']['id'] ?? json['supermarket_id'],
      supermarketName: json['supermarket']['name'] ?? json['supermarket_name'] ?? '',
      name: json['name'],
      latitude: json['latitude'] != null ? double.tryParse(json['latitude'].toString()) : null,
      longitude: json['longitude'] != null ? double.tryParse(json['longitude'].toString()) : null,
      city: json['city'] ?? 'Nairobi',
      address: json['address'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'supermarket_id': supermarketId,
      'supermarket_name': supermarketName,
      'name': name,
      'latitude': latitude,
      'longitude': longitude,
      'city': city,
      'address': address,
    };
  }
}
