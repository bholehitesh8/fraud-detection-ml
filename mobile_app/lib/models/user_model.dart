class UserModel {
  final int id;
  final String username;
  final String email;
  final String role;
  final bool isActive;
  final bool isLocked;
  final int failedLoginAttempts;
  final String? createdAt;
  final String? updatedAt;
  final String? lastLogin;

  UserModel({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    this.isActive = true,
    this.isLocked = false,
    this.failedLoginAttempts = 0,
    this.createdAt,
    this.updatedAt,
    this.lastLogin,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int? ?? 0,
      username: json['username'] as String? ?? '',
      email: json['email'] as String? ?? '',
      role: json['role'] as String? ?? 'analyst',
      isActive: json['is_active'] as bool? ?? true,
      isLocked: json['is_locked'] as bool? ?? false,
      failedLoginAttempts: json['failed_login_attempts'] as int? ?? 0,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
      lastLogin: json['last_login'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'role': role,
      'is_active': isActive,
      'is_locked': isLocked,
      'failed_login_attempts': failedLoginAttempts,
      'created_at': createdAt,
      'updated_at': updatedAt,
      'last_login': lastLogin,
    };
  }
}
