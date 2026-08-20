/* Galaxy English School - main.js
 * Global site behavior.
 *
 * Primary responsibility: power the mobile navigation (hamburger) menu.
 * The desktop nav is shown with `lg:flex` / `lg:hidden`, so this script only
 * needs to toggle the `hidden` class on the mobile menu below the `lg` breakpoint.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var menuBtn = document.getElementById('mobile-menu-btn');
        var mobileMenu = document.getElementById('mobile-menu');
        var hamburgerIcon = document.getElementById('hamburger-icon');
        var closeIcon = document.getElementById('close-icon');

        if (!menuBtn || !mobileMenu) {
            return;
        }

        var closeMenu = function () {
            mobileMenu.classList.add('hidden');
            if (hamburgerIcon) hamburgerIcon.classList.remove('hidden');
            if (closeIcon) closeIcon.classList.add('hidden');
            menuBtn.setAttribute('aria-expanded', 'false');
        };

        var openMenu = function () {
            mobileMenu.classList.remove('hidden');
            if (hamburgerIcon) hamburgerIcon.classList.add('hidden');
            if (closeIcon) closeIcon.classList.remove('hidden');
            menuBtn.setAttribute('aria-expanded', 'true');
        };

        var toggleMenu = function () {
            if (mobileMenu.classList.contains('hidden')) {
                openMenu();
            } else {
                closeMenu();
            }
        };

        // Toggle on hamburger click.
        menuBtn.addEventListener('click', function (event) {
            event.stopPropagation();
            toggleMenu();
        });

        // Close the menu when any link inside it is tapped.
        var links = mobileMenu.querySelectorAll('a');
        Array.prototype.forEach.call(links, function (link) {
            link.addEventListener('click', function () {
                closeMenu();
            });
        });

        // Close when the viewport grows to desktop (>= lg breakpoint).
        window.addEventListener('resize', function () {
            if (window.innerWidth >= 1024) {
                closeMenu();
            }
        });

        // Close when clicking anywhere outside the menu.
        document.addEventListener('click', function (event) {
            if (!mobileMenu.classList.contains('hidden')) {
                if (!mobileMenu.contains(event.target) && !menuBtn.contains(event.target)) {
                    closeMenu();
                }
            }
        });

        // Scroll-to-top button.
        var scrollTopBtn = document.getElementById('scroll-top-btn');
        if (scrollTopBtn) {
            var updateScrollBtn = function () {
                if (window.scrollY > 400) {
                    scrollTopBtn.classList.add('show');
                } else {
                    scrollTopBtn.classList.remove('show');
                }
            };
            window.addEventListener('scroll', updateScrollBtn);
            window.addEventListener('resize', updateScrollBtn);
            updateScrollBtn();
            scrollTopBtn.addEventListener('click', function () {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        }
    });
})();
