#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>

// Generate a random double between 0.0 and 1.0
double get_random_double(void) {
    uint32_t r;

#if defined(_WIN32) || defined(_WIN64)
    // Windows implementation using BCryptGenRandom
    #include <windows.h>
    #include <bcrypt.h>
    #pragma comment(lib, "bcrypt.lib")
    
    NTSTATUS status = BCryptGenRandom(NULL, (PUCHAR)&r, sizeof(r), 
                                      BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (!BCRYPT_SUCCESS(status)) {
        fprintf(stderr, "BCryptGenRandom failed: 0x%08x\n", status);
        exit(EXIT_FAILURE);
    }

#elif defined(__APPLE__) || defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__NetBSD__)
    // macOS/BSD implementation using arc4random
    arc4random_buf(&r, sizeof(r));

#else
    // Linux/Unix implementation with fallback
    #include <fcntl.h>
    #include <unistd.h>
    
    #if defined(__linux__) && defined(SYS_getrandom)
    #include <sys/syscall.h>
    
    // Try getrandom syscall first (Linux 3.17+)
    if (syscall(SYS_getrandom, &r, sizeof(r), 0) != sizeof(r)) {
        // Fall back to /dev/urandom if getrandom fails
        int fd = open("/dev/urandom", O_RDONLY);
        if (fd < 0 || read(fd, &r, sizeof(r)) != sizeof(r)) {
            fprintf(stderr, "Failed to get random bytes\n");
            if (fd >= 0) close(fd);
            exit(EXIT_FAILURE);
        }
        close(fd);
    }
    
    #else
    // Use /dev/urandom for other Unix systems
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd < 0 || read(fd, &r, sizeof(r)) != sizeof(r)) {
        fprintf(stderr, "Failed to read from /dev/urandom\n");
        if (fd >= 0) close(fd);
        exit(EXIT_FAILURE);
    }
    close(fd);
    #endif
#endif

    // Convert to double between 0.0 and 1.0
    return (double)r / UINT32_MAX;
}