/*
 * bitmask-launcher.c
 *
 * part of the bitmask bundle.
 * execute main entrypoint in a child folder inside the bundle.
 *
 * (c) LEAP Encryption Access Project, 2016.
 * License: GPL.
 *
*/

#include <unistd.h>
#include <stdlib.h>

char* const bitmask_path = "lib";
char* const entrypoint = "bitmask";

int main(int argc, char *argv[])
{
    argv[0] = entrypoint;
    chdir(bitmask_path);
    execv(entrypoint, argv);
}
