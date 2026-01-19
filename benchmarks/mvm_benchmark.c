#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

// Optional: gem5 magic instructions for region-of-interest statistics
#ifdef GEM5_ANNOTATIONS
#include "gem5/m5ops.h"
#else
#define m5_work_begin(workid, threadid)
#define m5_work_end(workid, threadid)
#define m5_dump_stats(delay, period)
#define m5_reset_stats(delay, period)
#endif

// Matrix-Vector Multiplication: y = A * x
void matrix_vector_multiply(double **A, double *x, double *y, int rows, int cols) {
    for (int i = 0; i < rows; i++) {
        y[i] = 0.0;
        for (int j = 0; j < cols; j++) {
            y[i] += A[i][j] * x[j];
        }
    }
}

int main(int argc, char *argv[]) {
    int rows = 256;
    int cols = 256;
    
    // Parse command-line arguments
    if (argc >= 2) {
        rows = atoi(argv[1]);
    }
    if (argc >= 3) {
        cols = atoi(argv[2]);
    }
    
    printf("Matrix-Vector Multiplication Benchmark\n");
    printf("Matrix size: %d x %d\n", rows, cols);
    printf("Vector size: %d\n", cols);
    
    // Allocate memory for matrix A
    double **A = (double **)malloc(rows * sizeof(double *));
    for (int i = 0; i < rows; i++) {
        A[i] = (double *)malloc(cols * sizeof(double));
    }
    
    // Allocate memory for vectors x and y
    double *x = (double *)malloc(cols * sizeof(double));
    double *y = (double *)malloc(rows * sizeof(double));
    
    // Initialize matrix A and vector x with simple values
    printf("Initializing data...\n");
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            A[i][j] = (double)((i + j) % 100) / 10.0;
        }
    }
    
    for (int j = 0; j < cols; j++) {
        x[j] = (double)(j % 50) / 5.0;
    }
    
    // Warm-up run
    printf("Warm-up run...\n");
    matrix_vector_multiply(A, x, y, rows, cols);
    
    // Start gem5 region of interest
    printf("Starting timed computation...\n");
    m5_reset_stats(0, 0);
    m5_work_begin(0, 0);
    
    // Perform matrix-vector multiplication
    matrix_vector_multiply(A, x, y, rows, cols);
    
    // End gem5 region of interest
    m5_work_end(0, 0);
    m5_dump_stats(0, 0);
    printf("Computation complete.\n");
    
    // Compute checksum for verification
    double checksum = 0.0;
    for (int i = 0; i < rows; i++) {
        checksum += y[i];
    }
    printf("Checksum: %.6f\n", checksum);
    
    // Print first few results for verification
    printf("First 5 results:\n");
    for (int i = 0; i < (rows < 5 ? rows : 5); i++) {
        printf("  y[%d] = %.6f\n", i, y[i]);
    }
    
    // Free memory
    for (int i = 0; i < rows; i++) {
        free(A[i]);
    }
    free(A);
    free(x);
    free(y);
    
    printf("Benchmark complete.\n");
    return 0;
}
