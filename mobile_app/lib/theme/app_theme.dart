import 'package:flutter/material.dart';

class AppTheme {
  // Brand Palette - Dark Graphite & Emerald / Teal
  static const Color darkGraphiteBackground = Color(0xFF0D0F12);
  static const Color darkGraphiteSurface = Color(0xFF16191F);
  static const Color darkGraphiteCard = Color(0xFF1E232B);
  static const Color darkGraphiteBorder = Color(0xFF2B323D);
  static const Color darkGraphiteBorderLight = Color(0xFF38414F);

  // Emerald & Teal Cybersecurity Accents
  static const Color emeraldPrimary = Color(0xFF00E599);
  static const Color emeraldDark = Color(0xFF00B074);
  static const Color emeraldGlow = Color(0x3300E599);
  static const Color tealSecondary = Color(0xFF00D2B4);
  static const Color cyanAccent = Color(0xFF00B4D8);

  // Status & Warning Colors
  static const Color errorRed = Color(0xFFFF4D4F);
  static const Color warningAmber = Color(0xFFFAAD14);
  static const Color infoBlue = Color(0xFF1890FF);

  // Typography Colors
  static const Color textHighEmphasis = Color(0xFFF1F5F9);
  static const Color textMediumEmphasis = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkGraphiteBackground,
      colorScheme: const ColorScheme(
        brightness: Brightness.dark,
        primary: emeraldPrimary,
        onPrimary: Color(0xFF003822),
        primaryContainer: Color(0xFF004D30),
        onPrimaryContainer: emeraldPrimary,
        secondary: tealSecondary,
        onSecondary: Color(0xFF00382F),
        secondaryContainer: Color(0xFF004D41),
        onSecondaryContainer: tealSecondary,
        tertiary: cyanAccent,
        onTertiary: Color(0xFF003544),
        error: errorRed,
        onError: Color(0xFF450A0A),
        surface: darkGraphiteSurface,
        onSurface: textHighEmphasis,
        surfaceContainerHighest: darkGraphiteCard,
        outline: darkGraphiteBorder,
        outlineVariant: darkGraphiteBorderLight,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: darkGraphiteSurface,
        elevation: 0,
        scrolledUnderElevation: 1,
        centerTitle: false,
        iconTheme: IconThemeData(color: emeraldPrimary),
        titleTextStyle: TextStyle(
          color: textHighEmphasis,
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.2,
        ),
      ),
      cardTheme: CardTheme(
        color: darkGraphiteCard,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: darkGraphiteBorder, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: emeraldPrimary,
          foregroundColor: const Color(0xFF002E1C),
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.3,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: emeraldPrimary,
          side: const BorderSide(color: emeraldPrimary, width: 1.2),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: darkGraphiteCard,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: darkGraphiteBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: darkGraphiteBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: emeraldPrimary, width: 1.5),
        ),
        labelStyle: const TextStyle(color: textMediumEmphasis),
        hintStyle: const TextStyle(color: textMuted),
      ),
      dividerTheme: const DividerThemeData(
        color: darkGraphiteBorder,
        thickness: 1,
        space: 1,
      ),
    );
  }
}
