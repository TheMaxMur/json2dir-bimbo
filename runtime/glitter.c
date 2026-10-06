#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <math.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* Glitter logistics: strings, purses, and POSIX. 💅👜
   The JSON grammar and json2dir algorithm are .bimbo. */
typedef struct { int64_t length; const unsigned char *data; } Gloss;
typedef struct Doll {
    int64_t kind, count, capacity;
    Gloss *text;
    Gloss **keys;
    struct Doll **values;
    unsigned char *bytes;
} Doll;
typedef struct Allocation { struct Allocation *next; max_align_t alignment; } Allocation;
static Allocation *allocations;
static int program_argc;

void bimbo_shutdown(void) {
    while (allocations) {
        Allocation *next = allocations->next;
        free(allocations);
        allocations = next;
    }
}

static _Noreturn void die(const char *message) {
    fprintf(stderr, "Error: %s. 💅💔\n", message);
    exit(1);
}

void bimbo_init(int argc) {
    program_argc = argc;
    if (atexit(bimbo_shutdown) != 0) die("couldn't attach the glitter cleanup crew");
}

static void *allocate(size_t size) {
    if (size > SIZE_MAX - sizeof(Allocation)) die("out of memory; the purse is empty");
    Allocation *item = calloc(1, sizeof(Allocation) + size);
    if (!item) die("out of memory; the purse is empty");
    item->next = allocations;
    allocations = item;
    return item + 1;
}

static Gloss *gloss(const unsigned char *data, int64_t size) {
    Gloss *s = allocate(sizeof(*s));
    s->length = size;
    s->data = data;
    return s;
}

void bimbo_panic(Gloss *message) {
    fputs("Error: ", stderr);
    fwrite(message->data, 1, (size_t)message->length, stderr);
    fputs(". 💔\n", stderr);
    exit(1);
}

void bimbo_spill(Gloss *message) {
    if (fwrite(message->data, 1, (size_t)message->length, stdout) != (size_t)message->length || putchar('\n') == EOF)
        die("couldn't spill to stdout");
}

int64_t bimbo_argc(void) { return program_argc; }
int64_t bimbo_length(Gloss *s) { return s->length; }
int64_t bimbo_byte(Gloss *s, int64_t index) {
    if (index < 0 || index >= s->length) die("byte index failed the vibecheck");
    return s->data[index];
}
Gloss *bimbo_slice(Gloss *s, int64_t start, int64_t end) {
    if (start < 0 || end < start || end > s->length) die("slice bounds failed the vibecheck");
    return gloss(s->data + start, end - start);
}
Gloss *bimbo_caption(int64_t number) {
    unsigned char *data = allocate(32);
    int n = snprintf((char *)data, 32, "%" PRId64, number);
    return gloss(data, n);
}
Gloss *bimbo_concat(Gloss *a, Gloss *b) {
    if (a->length > INT64_MAX - b->length) die("gloss is too long");
    int64_t size = a->length + b->length;
    unsigned char *data = allocate((size_t)size + 1);
    memcpy(data, a->data, (size_t)a->length);
    memcpy(data + a->length, b->data, (size_t)b->length);
    return gloss(data, size);
}
bool bimbo_equal(Gloss *a, Gloss *b) {
    return a->length == b->length && memcmp(a->data, b->data, (size_t)a->length) == 0;
}
int64_t bimbo_divide(int64_t a, int64_t b) {
    if (!b) die("division by zero; girl math has limits");
    return a == INT64_MIN && b == -1 ? INT64_MIN : a / b;
}
int64_t bimbo_modulo(int64_t a, int64_t b) {
    if (!b) die("modulo by zero; girl math has limits");
    return a == INT64_MIN && b == -1 ? 0 : a % b;
}
bool bimbo_affordable(int64_t high, int64_t low, int64_t exponent) {
    /* A generic numeric range primitive. The .bimbo parser constructs the limbs.
       Preserve serde_json's default u64 -> double -> scale rounding order. */
    if (high < 0 || high > 18446744073LL || low < 0 || low >= 1000000000LL ||
        (high == 18446744073LL && low > 709551615LL)) return false;
    uint64_t significand = (uint64_t)high * 1000000000ULL + (uint64_t)low;
    if (!significand || exponent <= 0) return true;
    if (exponent > 308) return false;
    char power[16];
    snprintf(power, sizeof(power), "1e%" PRId64, exponent);
    double value = (double)significand * strtod(power, NULL);
    return isfinite(value);
}

static Doll *doll(int64_t kind) {
    Doll *d = allocate(sizeof(*d));
    d->kind = kind;
    return d;
}
Doll *bimbo_lipstick(void) { return doll(4); }
Doll *bimbo_closet(void) { return doll(1); }
Doll *bimbo_accessory(Gloss *text) { Doll *d = doll(2); d->text = text; return d; }
Doll *bimbo_squad(void) { return doll(3); }
Doll *bimbo_basic(void) { return doll(0); }
int64_t bimbo_kind(Doll *d) { return d->kind; }
int64_t bimbo_size(Doll *d) { return d->count; }

static void require_kind(Doll *d, int64_t kind) {
    if (d->kind != kind) die("doll has the wrong outfit for this operation");
}
static void grow(Doll *d) {
    if (d->count < d->capacity) return;
    if (d->capacity > INT64_MAX / 2 / (int64_t)sizeof(void *)) die("the squad is too large");
    int64_t capacity = d->capacity ? d->capacity * 2 : 16;
    if (d->kind == 4) {
        unsigned char *data = allocate((size_t)capacity);
        if (d->count) memcpy(data, d->bytes, (size_t)d->count);
        d->bytes = data;
    } else {
        Doll **values = allocate((size_t)capacity * sizeof(*values));
        if (d->count) memcpy(values, d->values, (size_t)d->count * sizeof(*values));
        d->values = values;
        if (d->kind == 1) {
            Gloss **keys = allocate((size_t)capacity * sizeof(*keys));
            if (d->count) memcpy(keys, d->keys, (size_t)d->count * sizeof(*keys));
            d->keys = keys;
        }
    }
    d->capacity = capacity;
}
void bimbo_dab(Doll *d, int64_t value) {
    require_kind(d, 4);
    if (value < 0 || value > 255) die("lipstick only accepts bytes");
    grow(d);
    d->bytes[d->count++] = (unsigned char)value;
}
void bimbo_sparkle(Doll *d, int64_t cp) {
    if (cp < 0 || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) die("invalid Unicode code point");
    if (cp <= 0x7f) bimbo_dab(d, cp);
    else if (cp <= 0x7ff) {
        bimbo_dab(d, 0xc0 | (cp >> 6)); bimbo_dab(d, 0x80 | (cp & 63));
    } else if (cp <= 0xffff) {
        bimbo_dab(d, 0xe0 | (cp >> 12)); bimbo_dab(d, 0x80 | ((cp >> 6) & 63)); bimbo_dab(d, 0x80 | (cp & 63));
    } else {
        bimbo_dab(d, 0xf0 | (cp >> 18)); bimbo_dab(d, 0x80 | ((cp >> 12) & 63));
        bimbo_dab(d, 0x80 | ((cp >> 6) & 63)); bimbo_dab(d, 0x80 | (cp & 63));
    }
}
Gloss *bimbo_reveal(Doll *d) {
    require_kind(d, 4);
    unsigned char *data = allocate((size_t)d->count + 1);
    if (d->count) memcpy(data, d->bytes, (size_t)d->count);
    return gloss(data, d->count);
}
void bimbo_invite(Doll *d, Doll *value) {
    require_kind(d, 3); grow(d); d->values[d->count++] = value;
}
static int compare(Gloss *a, Gloss *b) {
    int64_t length = a->length < b->length ? a->length : b->length;
    int result = memcmp(a->data, b->data, (size_t)length);
    return result ? result : (a->length > b->length) - (a->length < b->length);
}
void bimbo_dress(Doll *d, Gloss *key, Doll *value) {
    require_kind(d, 1);
    /* Ordered map, matching serde_json's default BTreeMap; last duplicate wins. */
    int64_t lo = 0, hi = d->count;
    while (lo < hi) {
        int64_t mid = lo + (hi - lo) / 2;
        if (compare(d->keys[mid], key) < 0) lo = mid + 1; else hi = mid;
    }
    if (lo < d->count && compare(d->keys[lo], key) == 0) { d->values[lo] = value; return; }
    grow(d);
    memmove(d->keys + lo + 1, d->keys + lo, (size_t)(d->count - lo) * sizeof(*d->keys));
    memmove(d->values + lo + 1, d->values + lo, (size_t)(d->count - lo) * sizeof(*d->values));
    d->keys[lo] = key; d->values[lo] = value; d->count++;
}
Doll *bimbo_guest(Doll *d, int64_t index) {
    if ((d->kind != 1 && d->kind != 3) || index < 0 || index >= d->count) die("guest index failed the vibecheck");
    return d->values[index];
}
Gloss *bimbo_label(Doll *d, int64_t index) {
    require_kind(d, 1);
    if (index < 0 || index >= d->count) die("label index failed the vibecheck");
    return d->keys[index];
}
Gloss *bimbo_outfit(Doll *d) { require_kind(d, 2); return d->text; }

static bool utf8(Gloss *s) {
    for (int64_t i = 0; i < s->length;) {
        unsigned char c = s->data[i++];
        if (c < 0x80) continue;
        int extra;
        uint32_t cp, minimum;
        if (c >= 0xc2 && c <= 0xdf) { extra = 1; cp = c & 31; minimum = 0x80; }
        else if (c >= 0xe0 && c <= 0xef) { extra = 2; cp = c & 15; minimum = 0x800; }
        else if (c >= 0xf0 && c <= 0xf4) { extra = 3; cp = c & 7; minimum = 0x10000; }
        else return false;
        if (s->length - i < extra) return false;
        while (extra--) {
            unsigned char next = s->data[i++];
            if ((next & 0xc0) != 0x80) return false;
            cp = (cp << 6) | (next & 63);
        }
        if (cp < minimum || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) return false;
    }
    return true;
}
Gloss *bimbo_sip(void) {
    Doll *buffer = bimbo_lipstick();
    unsigned char chunk[8192];
    size_t n;
    while ((n = fread(chunk, 1, sizeof(chunk), stdin)) != 0)
        for (size_t i = 0; i < n; i++) bimbo_dab(buffer, chunk[i]);
    if (ferror(stdin)) die("couldn't read stdin to an internal representation");
    Gloss *s = bimbo_reveal(buffer);
    if (!utf8(s)) die("couldn't read stdin to an internal representation: invalid UTF-8");
    return s;
}

static _Noreturn void io_error(const char *operation, Gloss *path, int code) {
    fprintf(stderr, "Error: couldn't %s at \"", operation);
    fwrite(path->data, 1, (size_t)path->length, stderr);
    fprintf(stderr, "\": %s. The filesystem left us on read 💔📁\n", strerror(code));
    exit(1);
}
static const char *path_string(Gloss *path) {
    if (memchr(path->data, 0, (size_t)path->length)) io_error("use a path containing NUL", path, EINVAL);
    unsigned char *p = allocate((size_t)path->length + 1);
    memcpy(p, path->data, (size_t)path->length);
    return (char *)p;
}
void bimbo_unfollow(Gloss *path) { (void)unlink(path_string(path)); }
void bimbo_penthouse(Gloss *path) {
    const char *p = path_string(path);
    if (mkdir(p, 0777) != 0 && errno != EEXIST) io_error("create a directory", path, errno);
}
void bimbo_catwalk(Gloss *path) {
    if (chdir(path_string(path)) != 0) io_error("enter a directory", path, errno);
}
void bimbo_backstage(Gloss *context) {
    if (chdir("..") != 0) io_error("return to the parent directory", context, errno);
}
void bimbo_diary(Gloss *path, Gloss *content) {
    int fd = open(path_string(path), O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd == -1) io_error("create a regular file", path, errno);
    int64_t offset = 0;
    while (offset < content->length) {
        size_t remaining = (size_t)(content->length - offset);
        if (remaining > 1048576) remaining = 1048576;
        ssize_t n = write(fd, content->data + offset, remaining);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { int code = n < 0 ? errno : EIO; close(fd); io_error("write a regular file", path, code); }
        offset += n;
    }
    if (close(fd) != 0) io_error("close a regular file", path, errno);
}
void bimbo_heels(Gloss *path) {
    const char *p = path_string(path);
    struct stat st;
    if (stat(p, &st) != 0 || chmod(p, st.st_mode | 0111) != 0) io_error("make the script executable", path, errno);
}
void bimbo_situationship(Gloss *path, Gloss *target) {
    const char *p = path_string(path), *t = path_string(target);
    if (symlink(t, p) != 0) io_error("create a symlink", path, errno);
}
