#include <stdio.h>
#include <conio.h>
#include <alloc.h>

/* Structure for a Binary Tree Node */
struct Node {
    int data;
    struct Node *left, *right;
};

/* Structure for Stack */
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

/* Iterative Post-order Traversal using Two Stacks */
void iterativePostorder(struct Node* root) {
    struct Stack s1, s2;
    struct Node* node;
    s1.top = -1;
    s2.top = -1;

    if (root == NULL) return;

    /* Push root to first stack */
    push(&s1, root);

    /* Run while first stack is not empty */
    while (!isEmpty(&s1)) {
        /* Pop an item from s1 and push it to s2 */
        node = pop(&s1);
        push(&s2, node);

        /* Push left and right children of removed item to s1 */
        if (node->left)
            push(&s1, node->left);
        if (node->right)
            push(&s1, node->right);
    }

    /* Print all elements from second stack */
    while (!isEmpty(&s2)) {
        node = pop(&s2);
        printf("%d ", node->data);
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

    printf("Non-Recursive Post-order Traversal:\n");
    iterativePostorder(root);

    printf("\n\nPress any key to exit...");
    getch();
}