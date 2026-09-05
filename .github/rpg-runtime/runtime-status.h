/* Thread-safe browser lifecycle observations; no game or host-specific state. */
#ifndef MKXP_WEB_RUNTIME_STATUS_H
#define MKXP_WEB_RUNTIME_STATUS_H

#include <stdbool.h>

void runtime_frame_presented(void);
void runtime_restore_started(void);
void runtime_restore_finished(bool success);

#endif
