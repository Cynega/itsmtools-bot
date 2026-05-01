<?php
/**
 * Plugin Name: itsmtools-bot REST meta
 * Description: Registers Yoast SEO and theme subtitle meta keys so the
 *              itsmtools-bot pipeline can write them via the WordPress
 *              REST API (POST /wp/v2/posts → "meta" field).
 * Author: itsmtools-bot
 * Version: 1.0.0
 *
 * Install: copy this file to /wp-content/mu-plugins/itsmtools-bot-rest-meta.php
 * (create the mu-plugins folder if it does not exist). No activation needed,
 * WordPress auto-loads everything in mu-plugins/.
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('init', function () {
    $auth_cb = function () {
        return current_user_can('edit_posts');
    };

    // Yoast SEO — string fields
    $yoast_strings = [
        '_yoast_wpseo_focuskw',
        '_yoast_wpseo_metadesc',
        '_yoast_wpseo_title',
        '_yoast_wpseo_canonical',
    ];
    foreach ($yoast_strings as $key) {
        register_post_meta('post', $key, [
            'show_in_rest'  => true,
            'single'        => true,
            'type'          => 'string',
            'auth_callback' => $auth_cb,
        ]);
    }

    // Yoast SEO — primary category (integer)
    register_post_meta('post', '_yoast_wpseo_primary_category', [
        'show_in_rest'  => true,
        'single'        => true,
        'type'          => 'integer',
        'auth_callback' => $auth_cb,
    ]);

    // Theme / plugin subtitles — common keys. Whichever one your theme reads
    // from will display the value; the rest are ignored.
    $subtitle_keys = [
        'subtitle',
        '_subtitle',
        'wps_subtitle',
        'wp_subtitle',
        'post_subtitle',
        '_post_subtitle',
        'the_subtitle',
    ];
    foreach ($subtitle_keys as $key) {
        register_post_meta('post', $key, [
            'show_in_rest'  => true,
            'single'        => true,
            'type'          => 'string',
            'auth_callback' => $auth_cb,
        ]);
    }
});
