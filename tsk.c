#include <windows.h>
#include <stdio.h>
#include <tlhelp32.h>
#include <psapi.h>
#include <string.h>
#include <stdlib.h>

// ✅ Function to list all running processes
void listProcesses() {
    HANDLE hProcessSnap;
    PROCESSENTRY32 pe32;

    hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hProcessSnap == INVALID_HANDLE_VALUE) {
        printf("Failed to take process snapshot.\n");
        return;
    }

    pe32.dwSize = sizeof(PROCESSENTRY32);
    if (!Process32First(hProcessSnap, &pe32)) {
        CloseHandle(hProcessSnap);
        printf("Failed to get first process.\n");
        return;
    }

    printf("\n%-8s %-30s %-10s\n", "PID", "Process Name", "Memory (MB)");
    printf("----------------------------------------------------------\n");

    do {
        HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pe32.th32ProcessID);
        if (hProcess) {
            PROCESS_MEMORY_COUNTERS pmc;
            if (GetProcessMemoryInfo(hProcess, &pmc, sizeof(pmc))) {
                double memMB = (double)pmc.WorkingSetSize / (1024 * 1024);
                printf("%-8lu %-30ws %.2f\n", pe32.th32ProcessID, pe32.szExeFile, memMB);
            }
            CloseHandle(hProcess);
        }
    } while (Process32Next(hProcessSnap, &pe32));

    CloseHandle(hProcessSnap);
}

// ✅ Function to kill a process by PID
void killProcess(DWORD pid) {
    DWORD myPid = GetCurrentProcessId();
    if (pid == myPid) {
        printf("Error: Cannot kill this program itself.\n");
        return;
    }

    HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
    if (hProcess == NULL) {
        printf("Error: Unable to open process PID %lu (Error %lu)\n", pid, GetLastError());
        return;
    }

    if (TerminateProcess(hProcess, 0)) {
        printf("✅ Process %lu terminated successfully.\n", pid);
    } else {
        printf("❌ Failed to terminate PID %lu (Error %lu)\n", pid, GetLastError());
    }

    CloseHandle(hProcess);
}

// ✅ Function to start any process
void startProcess(const char *path) {
    char command[512];

    // Wrap in quotes for paths with spaces
    snprintf(command, sizeof(command), "start \"\" \"%s\"", path);

    int result = system(command);

    if (result != 0)
        printf("⚠️ Failed to start process: %s\n", path);
    else
        printf("✅ Started process: %s\n", path);
}

// ✅ Main menu
int main() {
    int choice;
    DWORD pid;
    char path[512];

    while (1) {
        printf("\n========== Advanced Task Manager ==========\n");
        printf("1. List running processes\n");
        printf("2. Kill a process (by PID)\n");
        printf("3. Start a new process\n");
        printf("4. Open Windows Task Manager\n");
        printf("5. Exit\n");
        printf("===========================================\n");
        printf("Enter choice: ");
        scanf("%d", &choice);
        getchar(); // clear input buffer

        switch (choice) {
        case 1:
            listProcesses();
            break;
        case 2:
            printf("Enter PID to terminate: ");
            scanf("%lu", &pid);
            killProcess(pid);
            break;
        case 3:
            printf("Enter full path or .exe name (e.g. notepad.exe or C:\\Program Files\\Microsoft VS Code\\Code.exe):\n> ");
            fgets(path, sizeof(path), stdin);
            path[strcspn(path, "\n")] = 0; // remove newline
            startProcess(path);
            break;
        case 4:
            system("start taskmgr");
            break;
        case 5:
            printf("Exiting program...\n");
            return 0;
        default:
            printf("Invalid option. Try again.\n");
        }
    }

    return 0;
}