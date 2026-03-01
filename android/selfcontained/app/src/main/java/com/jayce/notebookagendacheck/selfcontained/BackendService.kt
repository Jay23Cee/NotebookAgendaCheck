package com.jayce.notebookagendacheck.selfcontained

import android.app.Service
import android.content.Intent
import android.os.IBinder

/**
 * Phase 2 scaffold: responsible for owning embedded backend process lifecycle.
 */
class BackendService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // TODO(phase2): bootstrap embedded backend and publish health state.
        return START_STICKY
    }
}
