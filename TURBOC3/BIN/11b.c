#include <stdio.h>
#include <conio.h>
#include <alloc.h>

/* Structure for a Binary Tree Node */
struct Node {
    int data;
    struct Node *left, *right;
};

/* Structure for Stack to hold Node pointers */
struct Stack {
    int top;
    struct Node* items[20];
};

/* Stack Functions */
void push(struct Stack *s, struct Node *node) {
    s->items[++(s->top)] = node;
}

struct Node* pop(struct Stack *s) {
    return s->items[(s->top)--];
}

int isEmpty(struct Stack *s) {
    return s->top == -1;
}

/* Helper function to create a new Node */
struct Node* newNode(int data) {
    struct Node* node = (struct Node*)malloc(sizeof(struct Node));
    node->data = data;
    node->left = node->right = NULL;
    return node;
}

/* Iterative In-order Traversal */
void iterativeInorder(struct Node* root) {
    struct Stack s;
    struct Node* curr = root;
    s.top = -1;

    while (curr != NULL || !isEmpty(&s)) {
        /* Reach the left-most Node of the current Node */
        while (curr != NULL) {
            push(&s, curr);
            curr = curr->left;
        }

        /* Current must be NULL at this point */
        curr = pop(&s);

        printf("%d ", curr->data); /* Visit the root */

        /* We have visited the node and its left subtree.
           Now, it's the right subtree's turn */
        curr = curr->right;
    }
}

void main() {
    struct Node *root = NULL;
    clrscr();

    /* Creating the following tree:
              1
            /   \
           2     3
          / \
         4   5
    */
    root = newNode(1);
    root->left = newNode(2);
    root->right = newNode(3);
    root->left->left = newNode(4);
    root->left->right = newNode(5);

    printf("Non-Recursive In-order Traversal:\n");
    iterativeInorder(root);

    printf("\n\nPress any key to exit...");
    getch();
}