#include <stdio.h>
int hello (int arr[], int n ,int a){
    int count = 0 ;
    for (int i = 0;i<n; i++){
       if ( a== arr[i]){
          count = count + 1 ;
       }
    
    }
    return count ;
 }   



int main (){
    int arr[100000];
    int a ;
    scanf("%d",&a);
    int n;
    scanf("%d", &n);
    int count = hello(arr,a,n);
    printf("%d",count);
    return 0;
   }
