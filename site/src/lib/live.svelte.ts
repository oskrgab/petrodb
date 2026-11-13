import { onMount } from "svelte";

/**
 * Whether the page is running JavaScript: false in the prerendered HTML, true
 * once the component has mounted. Controls that cannot work without
 * JavaScript render only when `current` is true. Call it while a component
 * initialises.
 */
export function live(): { readonly current: boolean } {
  let current = $state(false);
  onMount(() => {
    current = true;
  });
  return {
    get current() {
      return current;
    },
  };
}
