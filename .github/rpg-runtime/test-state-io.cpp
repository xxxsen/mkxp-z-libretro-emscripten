// Exercise the actual patched RetroArch writer with a bounded WasmFS model.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <vector>

constexpr size_t payload_size = 1024 * 1024 + 24;
static size_t allocated, peak, limit;
template <class T> struct BoundedAllocator {
  using value_type = T;
  BoundedAllocator() = default;
  template <class U> BoundedAllocator(const BoundedAllocator<U>&) {}
  bool operator==(const BoundedAllocator&) const { return true; }
  T* allocate(size_t n) {
    const size_t bytes = n * sizeof(T);
    if (allocated + bytes > limit) throw std::bad_alloc();
    auto* p = static_cast<T*>(std::malloc(bytes));
    if (!p) throw std::bad_alloc();
    allocated += bytes;
    if (allocated > peak) peak = allocated;
    return p;
  }
  void deallocate(T* p, size_t n) { allocated -= n * sizeof(T); std::free(p); }
};
static std::vector<uint8_t, BoundedAllocator<uint8_t>> buffer;
struct intfstream_t { int unused; };
struct settings_t { struct { bool savestate_file_compression; } bools; } settings;
static bool open_failure, truncate_failure, write_failure, close_failure, flush_failure;
static unsigned closes, truncates;
static settings_t* config_get_ptr() { return &settings; }
static bool core_info_current_supports_savestate() { return true; }
static size_t core_serialize_size() { return payload_size - 24; }
static void* content_get_serialized_data(size_t* size) {
  *size = payload_size;
  void* p = std::malloc(*size);
  std::memset(p, 0x5a, *size);
  return p;
}
static intfstream_t* intfstream_open_file(const char*, int, int) {
  return open_failure ? nullptr : static_cast<intfstream_t*>(std::malloc(sizeof(intfstream_t)));
}
static intfstream_t* intfstream_open_rzip_file(const char* path, int mode) {
  return intfstream_open_file(path, mode, 0);
}
[[maybe_unused]] static int64_t intfstream_truncate(intfstream_t*, uint64_t size) {
  ++truncates;
  if (truncate_failure) return -1;
  buffer.resize(size);
  return 0;
}
static int64_t intfstream_write(intfstream_t*, const void* data, uint64_t size) {
  if (write_failure) return -1;
  // libc may split a large fwrite into aligned blocks and a final flush.
  for (size_t offset = 0; offset < size;) {
    const size_t count = std::min(size - offset, uint64_t(64 * 1024));
    if (offset + count > buffer.size()) buffer.resize(offset + count);
    std::memcpy(buffer.data() + offset, static_cast<const uint8_t*>(data) + offset, count);
    offset += count;
  }
  return size;
}
static int intfstream_close(intfstream_t*) { ++closes; return close_failure ? -1 : 0; }
[[maybe_unused]] static int intfstream_flush(intfstream_t*) { return flush_failure ? -1 : 0; }
#define RETRO_VFS_FILE_ACCESS_WRITE 1
#define RETRO_VFS_FILE_ACCESS_HINT_NONE 0
#define RARCH_LOG(...) ((void)0)
#define RARCH_ERR(...) ((void)0)
#include "actual-save.inc"

static void reset() {
  decltype(buffer) empty;
  buffer.swap(empty);
  peak = 0;
  closes = truncates = 0;
  open_failure = truncate_failure = write_failure = close_failure = flush_failure = false;
}
int main() {
  limit = payload_size + payload_size / 2;
  try {
    for (int failure = 0; failure < 6; ++failure) {
      reset();
      open_failure = failure == 1;
      truncate_failure = failure == 2;
      write_failure = failure == 3;
      close_failure = failure == 4;
      flush_failure = failure == 5;
      bool success = content_auto_save_state("game.state");
      assert(success == (failure == 0));
      assert(closes == (open_failure ? 0u : 1u));
      if (success) {
        assert(truncates == 1 && buffer.size() == payload_size && peak == payload_size);
        for (uint8_t value : buffer) assert(value == 0x5a);
      }
    }
    reset();
    settings.bools.savestate_file_compression = true;
    limit = 4 * payload_size;
    assert(content_auto_save_state("compressed.state"));
    assert(truncates == 0 && closes == 1);
    reset();
  } catch (const std::bad_alloc&) {
    std::fputs("raw state vector exceeded bounded peak allocation\n", stderr);
    return 1;
  }
}
