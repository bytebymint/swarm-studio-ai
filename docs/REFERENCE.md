# Implementation notes

The desktop implementation is independent. Separately supplied reference
materials are excluded from the repository and packaged application. Their
presence in a local development workspace does not grant permission to copy or
redistribute them.

## Desktop architecture

The application uses Qt WebEngine for rendered website inspection, a local
playback document for reconstruction, and a native bridge restricted to the
trusted application UI. Remote websites never receive access to that bridge.
Browser-extension APIs are not required by the desktop implementation.

The shared animation engine turns captured or generated DOM elements into
layout, text, image, media and component tasks. Cursor movement, typing carets,
selection boxes, measurement guides and task handoffs follow the application's
own task graph and choreography.

## Verification

Local fixtures cover document and nested scrolling, inline text, repeated
components, native controls, media, responsive layouts and isolated previews.
See [architecture](ARCHITECTURE.md) and [website creation](CREATION.md) for the
current implementation and its boundaries.

## Rights and distribution

The project license covers the original application materials. Third-party
runtime components retain their applicable notices and license terms. Website
content and separately supplied media remain subject to their owners' rights;
obtain permission where required before copying or redistributing them.
