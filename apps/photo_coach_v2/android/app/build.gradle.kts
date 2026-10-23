plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.photocoach.photo_coach_v2"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.photocoach.photo_coach_v2"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName

        // S3 起相机插件（camera_android_camerax）开始往包里带原生 .so。
        // 交付只出 arm64（--split-per-abi）：x86/x86_64 是给模拟器用的，
        // 真机包直接排除，体积更小，也少一类在旧机型上的加载风险。
        // 注意：只排除 x86*，**不要**写 "lib/*" 通配 —— 会把 arm64 也删掉。
        packaging {
            jniLibs {
                excludes += listOf("lib/x86/**", "lib/x86_64/**")
            }
        }
    }

    // ⚠️ debug 签名用仓库内 keystore（标准 Android debug 凭据，.gitignore 已排除 *.keystore）。
    // 原因（实测）：受限/沙箱环境下系统家目录不可写，AGP 默认自动生成
    // $HOME/.android/debug.keystore 会直接拒绝构建。凭据是公开的 debug 凭据，
    // 任何环境都可用 tool/build_apk.sh 复现（脚本会先确保 keystore 存在）。
    signingConfigs {
        getByName("debug") {
            storeFile = file("debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        release {
            // 正式版出包（S6）再配正式签名；当前 release 也用 debug 键，
            // 让 `flutter run --release` / 交付手测可用。
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
