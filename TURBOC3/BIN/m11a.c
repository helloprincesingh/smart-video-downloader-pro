#include <stdio.h>
#include <conio.h>
#include <stdlib.h>

// Node structure for binary tree
struct Node {
    int data;
    struct Node* left;
    struct Node* right;
};

// Stack structure for non-recursive traversal (fixed size for simplicity)
struct Stack {
    struct Node* arr[100]; // Max 100 nodes
    int top;
};

// Initialize stack
void initializeStack(struct Stack* s) {
    s->top = -1;
}

// Check if stack is empty
int isEmpty(struct Stack* s) {
    return s->top == -1;
}

// Push to stack
void push(struct Stack* s, struct Node* node) {
    if (s->top < 99) {
        s->arr[++(s->top)] = node;
    }
}

// Pop from stack
struct Node* pop(struct Stack* s) {
    if (!isEmpty(s)) {
        return s->arr[(s->top)--];
    }
    return NULL;
}

// Create a new node
struct Node* createNode(int data) {
    struct Node* newNode = (struct Node*)malloc(sizeof(struct Node));
    newNode->data = data;
    newNode->left = NULL;
    newNode->right = NULL;
    return newNode;
}

// Insert a node into BST (to build the tree)
struct Node* insert(struct Node* root, int data) {
    if (root == NULL) {
        return createNode(data);
    }
    if (data < root->data) {
        root->left = insert(root->left, data);
    } else if (data > root->data) {
        root->right = insert(root->right, data);
    }
    return root;
}

// Non-recursive Pre-order traversal
void preOrderNonRecursive(struct Node* root) {
    if (root == NULL) {
        printf("Tree is empty\n");
        return;
    }
    struct Stack s;
    initializeStack(&s);
    push(&s, root);
    printf("Pre-order traversal: ");
    while (!isEmpty(&s)) {
        struct Node* current = pop(&s);
        printf("%d ", current->data);
        // Push right first, then left (so left is processed first)
        if (current->right != NULL) {
            push(&s, current->right);
        }
        if (current->left != NULL) {
            push(&s, current->left);
        }
    }
    printf("\n");
}

// Main function
void main() {
    struct Node* root = NULL;
    int choice, data;
    clrscr();
    // Build a sample tree for demonstration
    root = insert(root, 50);
    insert(root, 30);
    insert(root, 70);
    insert(root, 20);
    insert(root, 40);
    insert(root, 60);
    insert(root, 80);
    printf("Sample BST created with nodes: 50, 30, 70, 20, 40, 60, 80\n");
    while (1) {
        printf("\nBinary Tree Operations:\n");
        printf("1. Insert an element\n");
        printf("2. Pre-order Traversal (Non-recursive)\n");
        printf("3. Exit\n");
        printf("Enter choice: ");
        scanf("%d", &choice);
        switch (choice) {
            case 1:
                printf("Enter element to insert: ");
                scanf("%d", &data);
                root = insert(root, data);
                printf("Inserted %d\n", data);
                break;
            case 2:
                preOrderNonRecursive(root);
                break;
            case 3:
                exit(0);
            default:
                printf("Invalid choice!\n");
        }
    }
    getch();
}