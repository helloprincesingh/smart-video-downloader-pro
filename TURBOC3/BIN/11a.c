#include <stdio.h>
#include <conio.h>
#include <alloc.h>

struct Node {
    int data;
    struct Node *left, *right;
};

struct Stack {
    int top;
    struct Node* items[20];
};

void push(struct Stack *s, struct Node *node) {
    s->items[++(s->top)] = node;
}

struct Node* pop(struct Stack *s) {
    return s->items[(s->top)--];
}

int isEmpty(struct Stack *s) {
    return s->top == -1;
}

struct Node* newNode(int data) {
    struct Node* node = (struct Node*)malloc(sizeof(struct Node));
    node->data = data;
    node->left = node->right = NULL;
    return node;
}

/* Function to build a tree based on user input */
struct Node* createTree() {
    int val;
    struct Node* temp;

    printf("Enter node value (-1 for no node): ");
    scanf("%d", &val);

    if (val == -1) {
        return NULL;
    }

    temp = newNode(val);

    printf("Entering left child of %d:\n", val);
    temp->left = createTree();

    printf("Entering right child of %d:\n", val);
    temp->right = createTree();

    return temp;
}

void iterativePreorder(struct Node* root) {
    struct Stack s;
    s.top = -1;

    if (root == NULL) {
        printf("Tree is empty.\n");
        return;
    }

    push(&s, root);

    while (!isEmpty(&s)) {
        struct Node* curr = pop(&s);
        printf("%d ", curr->data);

        /* Push right child first so left is processed first */
        if (curr->right)
            push(&s, curr->right);
        if (curr->left)
            push(&s, curr->left);
    }
}

void main() {
    struct Node *root = NULL;
    clrscr();

    printf("--- Build Your Binary Tree ---\n");
    root = createTree();

    printf("\nNon-Recursive Pre-order Traversal:\n");
    iterativePreorder(root);

    printf("\n\nPress any key to exit...");
    getch();
}