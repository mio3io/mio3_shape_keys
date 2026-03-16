<p align="center">
  <a href="README.md">English</a> |
  <a href="README-JP.md">日本語</a>
</p>

# Mio3 Shape Keys

An integrated shape key management tool specialized for character modeling.

## Download

https://addon.mio3io.com/

## Documentation

[Mio3 Shape Keys Ver3 Documentation (WIP)](https://addon.mio3io.com/#/ja/mio3shapekeys/)


## Main Features Added in Ver3

-   Shape key sync and automatic editing
-   Apply modifiers while preserving shape keys
-   Batch transfer of shape keys between meshes with different topology
-   Create left/right shape keys
-   Create opposite-side shape keys
-   Tagging
-   Shape key value preset registration
-   Grouping (default: keys with names starting with "===" are grouped)
-   Move and sort by group
-   Multi-select system
-   Batch operations on selected keys
-   Find keys matching specific conditions (unused, error causes, etc.)
-   Shape key smoothing
-   Symmetrize shape
-   Mirror shape (left/right)
-   Invert shape movement amount
-   Copy and paste shape
-   Clear vertices that have not moved beyond a threshold
-   Materialize shape keys as objects
-   Protect and repair shape keys (e.g., blink) that break when applied to Basis

## Ver2

Ver2 can be downloaded from [releases](https://github.com/mio3io/mio3_shape_keys/releases).


## Changelog  
version = "3.0.0-beta-20260315"
https://youtu.be/vK5ssYbRR2o

Added ability to remove drivers from selected shape keys
- New operator to remove drivers from active, selected, or all shape keys.

[Added transfer properties](https://github.com/WolfExplode/mio3_shape_keys_english/commit/08a26b8643530a09e708ecf5639c438badd04c75)
- Transfer Properties option added to the Transfer Shape Key dialog (mute, slider range, vertex group, tags, composer rules).

[Optimized Transfer](https://github.com/WolfExplode/mio3_shape_keys_english/commit/3df7a487d14fda53a59486bdcfe647b3497fecd6)
- Vectorized interpolation, scipy cKDTree fallback, buffer reuse, matrix precomputation. ~60% faster on large meshes.

[Added transfer properties operator](https://github.com/WolfExplode/mio3_shape_keys_english/commit/909662d7b383b003dd79630e94ae5847b15b0604)
- Standalone Transfer Properties operator for two objects with matching shape key names.

[Added Transfer Shape Key operator](https://github.com/WolfExplode/mio3_shape_keys_english/commit/7b92102b26e9e012bf0bad162ba0750fe81ce05a)
- Transfers the drivers according to shape key name

[Added new operator "Set Value To Zero"](https://github.com/WolfExplode/mio3_shape_keys_english/commit/9e1b6ea22cf99bc06eabd21c2f55356f9bdfbdd8)
- sets the selected shape keys value to zero

[Added new operator create vertex group from selected shape keys](https://github.com/WolfExplode/mio3_shape_keys_english/commit/41536d34ffc962b8293f53d767f7d4df8a16eff6)










