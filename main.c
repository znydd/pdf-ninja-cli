#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[]){
    if (argc <= 2)
    { 
        if (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0)
        {
            printf("Helps docs\n");
        }
    }


    return 0;
}