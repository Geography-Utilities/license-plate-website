# Requirements (MKA)
## User Accounts
### Account Creation
- Required: username, password, email (?)
- Optional: name (?), ALPCA #, discord account

### Storing account information
- Securely store hashed + salted passwords
- Relation to submitted plates (see below)

## Plate database
### Display

- organized by category (states)
        - subcategories within states
        - county-coding subcategory first, then type for types county-coded
        - no county coding -> plates types only subcategory
        - tribal plates are their own category
        - only two levels of subcategory?
- plates displayed per subcategory
- record current high reported, including value, date, user, opt. picture
        - if store all submissions, record lowest as well
        - need a way to disambiguate ties: save submission timestamp
- collapsible sections -- make it look good

### Verification
- not sure what y'all want to do here, if plates should be automatically accepted or approved by some set of moderators

### Storage

- internal identifier for plate. either generated ID or custom short form
        - plate should record vehicle type (passenger, motorcycle, truck, etc.) and plate type (std., specialty, etc.)
- history of high-number submissions?
        - maybe custom index if plate format changes
- store plate number, date spotted, date submitted, user submitted, opt. location (coords) and opt. picture
- add verification field (for location and/or picture)
        - add multiple users on a submission if they were also there
        - use 64-bit timestamps
- so relation to user (above) and link to picture storage

## Hosting
- web server
- database (relational?)
- Images (bucket?)

# Current TODO List (penguin)
1. per-page authentication (v. high priority)
2. data structure and storage
        - this should should be simple to execute with jinja table templating and database calls. need to figure out what database structure i want to use exactly; probably postgresql
        - image storage?? thoughts are currently cache latest 3 subm. for each type, downscale on reciept
3. plate overlay formatting and style
        - vague ideas on how to do this
        - need to acquire fonts
        - somebody other than me source images please
4. figure out exact flask structure for multiple pages with same template. how to have list of states w/ individually formatted pages (shouldn't be too bad)
5. proper full site formatting
        - somebody else do graphic design, i can do css
6. fix login redirect to maintain current page, not redirect to /