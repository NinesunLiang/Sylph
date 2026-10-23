package com.photocoach.photo_coach_v2

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.util.Log
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

/**
 * v0.4.0：原生相机桥。
 *
 * 产品流程：预览页（App 内取景）觉得光线/姿势都好了 → 点快门 →
 * 拉起**系统相机**（App 静默退到后台）→ 用户拍完回 App →
 * App 从 MediaStore 里捞出刚拍的那张，展示 + 一键送教练点评。
 *
 * 为什么能直接读 MediaStore：AndroidManifest 里早就为了「教练页选相册图」
 * 申请了 READ_MEDIA_IMAGES（API 33+）/ READ_EXTERNAL_STORAGE（≤32），
 * 系统相机拍的照片 App 读得到，不需要新增权限。
 */
class MainActivity : FlutterActivity() {

    companion object {
        private const val CHANNEL = "photo_coach.v2/native_camera"
        private const val TAG = "NativeCamera"

        // API 26 起的专用「静照片相机」intent；老系统退回经典 IMAGE_CAPTURE。
        // 不指定 extra_OUTPUT：指定了只能拍到 App 私有目录，用户相册里没有，
        // 也就无法"配合系统相机的相册"这个产品前提。
        private fun captureIntent(): Intent =
            Intent(
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                    MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA
                else "android.media.action.IMAGE_CAPTURE"
            )
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor, CHANNEL)
            .setMethodCallHandler { call, reply ->
                when (call.method) {
                    "launchNativeCamera" ->
                        reply.success(launchCamera())

                    "latestImageSince" ->
                        // Dart 侧传的是裸 int（invokeMethod 的 argument 位置），
                        // 不是 Map —— 用 call.arguments 直取，别用 argument(name)。
                        reply.success(latestImageSince((call.arguments as? Number)?.toLong() ?: 0L))

                    else -> reply.notImplemented()
                }
            }
    }

    /** 拉起系统相机。返回 false 表示这台设备上没装可用相机（用户自己会明白）。 */
    private fun launchCamera(): Boolean = try {
        startActivity(captureIntent())
        true
    } catch (e: Exception) {
        Log.w(TAG, "no camera app available", e)
        false
    }

    /**
     * [sinceMillis] 之后新增的最新一张照片：
     * 从 MediaStore 里捞出来，拷进 App 缓存目录，返回**本地文件路径**
     * （Flutter 侧用 Image.file 直接显示；原文件在系统相册里，不动它）。
     * 没有新照片（比如用户在相机里取消了）返回 null。
     */
    private fun latestImageSince(sinceMillis: Long): String? {
        if (sinceMillis <= 0) return null
        val sinceSeconds = sinceMillis / 1000

        val projection = arrayOf(MediaStore.Images.Media._ID)
        val selection = "${MediaStore.Images.Media.DATE_ADDED} >= ?"
        val args = arrayOf(sinceSeconds.toString())
        val sortOrder =
            "${MediaStore.Images.Media.DATE_ADDED} DESC, ${MediaStore.Images.Media._ID} DESC"

        val uri: Uri? = runCatching {
            contentResolver.query(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                projection, selection, args, sortOrder
            )?.use { cursor ->
                // if 必须带 else：不带的话整个表达式类型变成 Unit?，
                // runCatching 的返回值就和 Uri? 对不上了（编译错误）。
                if (cursor.moveToFirst()) {
                    cursor.getString(0)?.let { id ->
                        Uri.parse("content://media/external/images/media/$id")
                    }
                } else null
            }
        }.getOrNull()

        if (uri == null) return null

        val out = File(cacheDir, "native_shot_${System.currentTimeMillis()}.jpg")
        return runCatching {
            contentResolver.openInputStream(uri)?.use { input ->
                out.outputStream().use { o -> input.copyTo(o) }
            }
            if (out.length() > 0) out.absolutePath
            else {
                out.delete()
                null
            }
        }.getOrNull()
    }
}
