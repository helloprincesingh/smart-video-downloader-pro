#include <stdio.h>
#include <conio.h>

/* Function to swap two elements */
void swap(int* a, int* b) {
    int t = *a;
    *a = *b;
    *b = t;
}

/* Partition function to place pivot at right position */
int partition(int arr[], int low, int high) {
    int pivot = arr[high]; // Choosing the last element as pivot
    int i = (low - 1);    // Index of smaller element
    int j;

    for (j = low; j <= high - 1; j++) {
        // If current element is smaller than or equal to pivot
        if (arr[j] <= pivot) {
            i++; 
            swap(&arr[i], &arr[j]);
        }
    }
    swap(&arr[i + 1], &arr[high]);
    return (i + 1);
}

/* Main function that implements Quick Sort */
void quickSort(int arr[], int low, int high) {
    if (low < high) {
        /* pi is partitioning index, arr[p] is now at right place */
        int pi = partition(arr, low, high);

        /* Separately sort elements before partition and after partition */
        quickSort(arr, low, pi - 1);
        quickSort(arr, pi + 1, high);
    }
}

void main() {
    int arr[20], n, i;
    clrscr(); // Clears the Turbo C output screen

    printf("--- Quick Sort Program ---\n");
    printf("Enter number of elements (max 20): ");
    scanf("%d", &n);

    printf("Enter %d elements:\n", n);
    for (i = 0; i < n; i++) {
        scanf("%d", &arr[i]);
    }

    quickSort(arr, 0, n - 1);

    printf("\nSorted array in ascending order:\n");
    for (i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }

    printf("\n\nPress any key to exit...");
    getch(); // Holds the screen until a key is pressed
}