package com.jayce.notebookagendacheck.launcher

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var loadingBar: ProgressBar
    private lateinit var stateText: TextView
    private lateinit var offlineContainer: View
    private lateinit var retryButton: Button
    private lateinit var openTermuxButton: Button

    private val worker: ExecutorService = Executors.newSingleThreadExecutor()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.web_view)
        loadingBar = findViewById(R.id.loading_bar)
        stateText = findViewById(R.id.state_text)
        offlineContainer = findViewById(R.id.offline_container)
        retryButton = findViewById(R.id.retry_button)
        openTermuxButton = findViewById(R.id.open_termux_button)

        configureWebView()

        retryButton.setOnClickListener {
            probeBackendAndLoad()
        }
        openTermuxButton.setOnClickListener {
            openTermux()
        }

        probeBackendAndLoad()
    }

    override fun onDestroy() {
        super.onDestroy()
        worker.shutdownNow()
        webView.destroy()
    }

    private fun configureWebView() {
        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            setSupportMultipleWindows(false)
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
        }

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val targetUrl = request?.url?.toString().orEmpty()
                return !isAllowedUrl(targetUrl)
            }
        }
    }

    private fun isAllowedUrl(url: String): Boolean {
        return url.startsWith(APP_BASE_URL)
    }

    private fun probeBackendAndLoad() {
        showLoadingState()
        worker.execute {
            val healthy = isBackendHealthy()
            runOnUiThread {
                if (healthy) {
                    showConnectedState()
                } else {
                    showOfflineState(getString(R.string.state_offline))
                }
            }
        }
    }

    private fun isBackendHealthy(): Boolean {
        var connection: HttpURLConnection? = null
        return try {
            connection = URL(HEALTH_URL).openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.connectTimeout = 1200
            connection.readTimeout = 1200
            connection.instanceFollowRedirects = false
            connection.useCaches = false

            if (connection.responseCode != 200) {
                return false
            }

            val body = BufferedReader(InputStreamReader(connection.inputStream)).use { reader ->
                reader.readText()
            }
            val json = JSONObject(body)
            json.optString("status") == "ok" && json.optString("app") == HEALTH_APP_NAME
        } catch (_: Exception) {
            false
        } finally {
            connection?.disconnect()
        }
    }

    private fun showLoadingState() {
        loadingBar.visibility = View.VISIBLE
        stateText.visibility = View.VISIBLE
        stateText.text = getString(R.string.state_loading)
        offlineContainer.visibility = View.GONE
        webView.visibility = View.GONE
    }

    private fun showConnectedState() {
        loadingBar.visibility = View.GONE
        stateText.visibility = View.GONE
        offlineContainer.visibility = View.GONE
        webView.visibility = View.VISIBLE
        if (webView.url != APP_BASE_URL) {
            webView.loadUrl(APP_BASE_URL)
        }
    }

    private fun showOfflineState(message: String) {
        loadingBar.visibility = View.GONE
        stateText.visibility = View.VISIBLE
        stateText.text = message
        offlineContainer.visibility = View.VISIBLE
        webView.visibility = View.GONE
    }

    private fun openTermux() {
        val launchIntent = packageManager.getLaunchIntentForPackage(TERMUX_PACKAGE)
        if (launchIntent != null) {
            startActivity(launchIntent)
            return
        }

        val fallbackIntent = Intent(Intent.ACTION_VIEW, Uri.parse(TERMUX_PLAY_URL))
        if (fallbackIntent.resolveActivity(packageManager) != null) {
            startActivity(fallbackIntent)
        } else {
            Toast.makeText(this, getString(R.string.termux_not_found), Toast.LENGTH_SHORT).show()
        }
    }

    companion object {
        private const val APP_BASE_URL = "http://127.0.0.1:8080"
        private const val HEALTH_URL = "http://127.0.0.1:8080/_nach/health"
        private const val HEALTH_APP_NAME = "NotebookAgendaCheck"
        private const val TERMUX_PACKAGE = "com.termux"
        private const val TERMUX_PLAY_URL = "https://play.google.com/store/apps/details?id=com.termux"
    }
}
